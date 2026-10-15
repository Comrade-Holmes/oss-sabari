from typing import Any, Dict, List, Optional
from app.database import db

class AllergyCheckerRepository:
    def check_allergies(
        self,
        allergen_ids: List[str],
        match_mode: str = "ANY",
        restaurant_id: Optional[str] = None,
        city: Optional[str] = None,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        if not allergen_ids:
            return []

        where_clauses = ["r IS NOT NULL", "d IS NOT NULL"]
        params: Dict[str, Any] = {
            "selected_allergens": allergen_ids,
            "target_count": len(allergen_ids)
        }

        if restaurant_id:
            where_clauses.append("r.id = $restaurant_id")
            params["restaurant_id"] = restaurant_id.strip()
        if city:
            where_clauses.append("toLower(r.city) = toLower($city)")
            params["city"] = city.strip()
        if category:
            where_clauses.append("toLower(d.category) = toLower($category)")
            params["category"] = category.strip()

        # Query traversing Restaurant -> Dish -> Ingredient -> Allergen and Dish -> MAY_CONTAIN -> Allergen
        query = f"""
        MATCH (r:Restaurant)-[:OFFERS]->(d:Dish)
        WHERE {' AND '.join(where_clauses)}
        
        // Find ingredients of this dish
        OPTIONAL MATCH (d)-[:CONTAINS]->(i:Ingredient)
        OPTIONAL MATCH (i)-[:CONTAINS_ALLERGEN]->(ia:Allergen)
        
        // Find precautionary MAY_CONTAIN allergens
        OPTIONAL MATCH (d)-[:MAY_CONTAIN]->(mca:Allergen)
        
        WITH r, d,
             count(DISTINCT i) as total_ingredients,
             collect(DISTINCT {{
                 ingredient_id: i.id,
                 ingredient_name: i.name,
                 verification_status: i.verification_status,
                 source_reference: i.source_reference,
                 allergen_id: ia.id,
                 allergen_name: ia.name
             }}) as all_ing_allergen_links,
             collect(DISTINCT {{
                 allergen_id: mca.id,
                 allergen_name: mca.name
             }}) as all_may_contain_links

        // Filter matched ingredients to only those matching the selected allergen IDs
        WITH r, d, total_ingredients, all_ing_allergen_links, all_may_contain_links,
             [x IN all_ing_allergen_links WHERE x.allergen_id IN $selected_allergens] as matched_ingredients,
             [x IN all_may_contain_links WHERE x.allergen_id IN $selected_allergens] as matched_may_contain

        // Extract distinct matched allergen IDs
        WITH r, d, total_ingredients, matched_ingredients, matched_may_contain,
             ([x IN matched_ingredients | x.allergen_id] + [y IN matched_may_contain | y.allergen_id]) as raw_matched_ids
        
        WITH r, d, total_ingredients, matched_ingredients, matched_may_contain,
             reduce(acc = [], x IN raw_matched_ids | CASE WHEN x IN acc THEN acc ELSE acc + [x] END) as matched_allergen_ids,
             reduce(acc = [], x IN [m IN matched_ingredients | m.allergen_name] + [n IN matched_may_contain | n.allergen_name] | CASE WHEN x IN acc THEN acc ELSE acc + [x] END) as matched_allergen_names

        // Filter based on MatchMode: ANY (at least 1) or ALL (all selected allergen IDs found)
        WHERE (
            ($match_mode = 'ANY' AND size(matched_allergen_ids) > 0)
            OR
            ($match_mode = 'ALL' AND size(matched_allergen_ids) = $target_count)
        )

        RETURN r, d, total_ingredients, matched_ingredients, matched_may_contain, matched_allergen_names, matched_allergen_ids
        ORDER BY r.name ASC, d.name ASC
        """
        params["match_mode"] = match_mode.upper()

        records = db.execute_query(query, params)
        results = []

        for rec in records:
            r = dict(rec["r"])
            d = dict(rec["d"])
            total_ing = rec["total_ingredients"]
            matched_ings = [m for m in rec["matched_ingredients"] if m.get("ingredient_id") and m.get("allergen_id")]
            matched_may = [m for m in rec["matched_may_contain"] if m.get("allergen_id")]
            matched_names = rec["matched_allergen_names"]

            # Determine data completeness flags
            data_status = d.get("ingredient_data_status", "PARTIAL")
            is_incomplete = (data_status != "COMPLETE") or (total_ing == 0)

            # Categorize match evidence
            has_direct_ingredient_match = len(matched_ings) > 0
            has_precautionary_match = len(matched_may) > 0

            # Safety summary string
            if has_direct_ingredient_match and has_precautionary_match:
                safety_summary = "CONTAINS MATCHED ALLERGENS (Direct ingredient & precautionary cross-contact)"
            elif has_direct_ingredient_match:
                safety_summary = "CONTAINS MATCHED ALLERGENS (Direct recorded ingredient)"
            else:
                safety_summary = "PRECAUTIONARY CROSS-CONTACT WARNING (May contain allergen)"

            if is_incomplete:
                safety_summary += " — Incomplete ingredient records require verbal restaurant confirmation"

            item = {
                "restaurant_id": r["id"],
                "restaurant_name": r["name"],
                "restaurant_city": r.get("city", ""),
                "dish_id": d["id"],
                "dish_name": d["name"],
                "dish_category": d.get("category", "Main Course"),
                "dish_price": d.get("price", 0.0),
                "vegetarian": d.get("vegetarian", False),
                "vegan": d.get("vegan", False),
                "ingredient_data_status": data_status,
                "total_ingredients_recorded": total_ing,
                "is_incomplete": is_incomplete,
                "matched_allergen_names": matched_names,
                "matched_ingredients": matched_ings,
                "matched_may_contain": matched_may,
                "safety_summary": safety_summary
            }
            results.append(item)

        return results

allergy_checker_repo = AllergyCheckerRepository()
