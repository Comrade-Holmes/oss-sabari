import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from app.database import db

def _s(value: Any, default: str = "") -> str:
    """Coerce None / Enum / str to a clean plain str for Neo4j."""
    if value is None:
        return default
    value = getattr(value, "value", value)
    return str(value).strip()


class DishRepository:
    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def get_by_id(self, dish_id: str) -> Optional[Dict[str, Any]]:
        query = """
        MATCH (d:Dish {id: $id})
        OPTIONAL MATCH (r:Restaurant)-[:OFFERS]->(d)
        OPTIONAL MATCH (d)-[:CONTAINS]->(i:Ingredient)
        OPTIONAL MATCH (i)-[:CONTAINS_ALLERGEN]->(ia:Allergen)
        OPTIONAL MATCH (d)-[:MAY_CONTAIN]->(mca:Allergen)
        WITH d,
             collect(DISTINCT {id: r.id, name: r.name, city: r.city, cuisine_type: r.cuisine_type}) as restaurants,
             collect(DISTINCT {
                 id: i.id, 
                 name: i.name, 
                 category: i.category, 
                 verification_status: i.verification_status,
                 source_reference: i.source_reference
             }) as ingredients,
             collect(DISTINCT {id: ia.id, name: ia.name, allergen_category: ia.allergen_category}) as allergens,
             collect(DISTINCT {id: mca.id, name: mca.name, allergen_category: mca.allergen_category}) as may_contain_allergens
        RETURN d, restaurants, ingredients, allergens, may_contain_allergens
        LIMIT 1
        """
        record = db.execute_single(query, {"id": dish_id})
        if not record or not record.get("d"):
            return None
        dish = dict(record["d"])
        dish["restaurants"] = [r for r in record["restaurants"] if r.get("id")]
        dish["ingredients"] = [i for i in record["ingredients"] if i.get("id")]
        dish["allergens"] = [a for a in record["allergens"] if a.get("id")]
        dish["may_contain_allergens"] = [m for m in record["may_contain_allergens"] if m.get("id")]
        return dish

    # Relationship definitions: (param name, target label, rel pattern direction)
    _REL_QUERIES = {
        "restaurants": """
            MATCH (d:Dish {id: $id})
            UNWIND $ids AS target_id
            MATCH (t:Restaurant {id: target_id})
            MERGE (t)-[:OFFERS]->(d)
        """,
        "ingredients": """
            MATCH (d:Dish {id: $id})
            UNWIND $ids AS target_id
            MATCH (t:Ingredient {id: target_id})
            MERGE (d)-[:CONTAINS]->(t)
        """,
        "may_contain": """
            MATCH (d:Dish {id: $id})
            UNWIND $ids AS target_id
            MATCH (t:Allergen {id: target_id})
            MERGE (d)-[:MAY_CONTAIN]->(t)
        """,
    }
    _REL_CLEAR = {
        "restaurants": "MATCH (:Restaurant)-[rel:OFFERS]->(d:Dish {id: $id}) DELETE rel",
        "ingredients": "MATCH (d:Dish {id: $id})-[rel:CONTAINS]->(:Ingredient) DELETE rel",
        "may_contain": "MATCH (d:Dish {id: $id})-[rel:MAY_CONTAIN]->(:Allergen) DELETE rel",
    }

    @staticmethod
    def _clean_ids(ids: Optional[List[str]]) -> List[str]:
        seen: List[str] = []
        for x in ids or []:
            x = str(x).strip()
            if x and x not in seen:
                seen.append(x)
        return seen

    def _set_relationships(self, dish_id: str, *, restaurant_ids=None, ingredient_ids=None, may_contain_allergen_ids=None) -> None:
        """Replace relationships for every kind that is not None (None = leave untouched).
        Runs in ONE transaction so a failure cannot leave a half-updated dish."""
        plan = [
            ("restaurants", restaurant_ids),
            ("ingredients", ingredient_ids),
            ("may_contain", may_contain_allergen_ids),
        ]
        plan = [(k, self._clean_ids(v)) for k, v in plan if v is not None]
        if not plan:
            return
        with db.get_session() as session:
            def _tx(tx):
                for kind, ids in plan:
                    tx.run(self._REL_CLEAR[kind], {"id": dish_id}).consume()
                    if ids:
                        tx.run(self._REL_QUERIES[kind], {"id": dish_id, "ids": ids}).consume()
            session.execute_write(_tx)

    def create(self, data: Dict[str, Any], restaurant_ids: Optional[List[str]] = None, ingredient_ids: Optional[List[str]] = None, may_contain_allergen_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        dish_id = str(uuid.uuid4())
        now = self._now_iso()
        query = """
        CREATE (d:Dish {
            id: $id,
            name: $name,
            description: $description,
            category: $category,
            price: $price,
            vegetarian: $vegetarian,
            vegan: $vegan,
            preparation_notes: $preparation_notes,
            availability_status: $availability_status,
            ingredient_data_status: $ingredient_data_status,
            created_at: $now,
            updated_at: $now
        })
        RETURN d.id as id
        """
        params = {
            "id": dish_id,
            "name": _s(data.get("name"), ""),
            "description": _s(data.get("description"), ""),
            "category": _s(data.get("category"), "Main Course"),
            "price": float(data.get("price") or 0.0),
            "vegetarian": bool(data.get("vegetarian", False)),
            "vegan": bool(data.get("vegan", False)),
            "preparation_notes": _s(data.get("preparation_notes"), ""),
            "availability_status": _s(data.get("availability_status"), "AVAILABLE"),
            "ingredient_data_status": _s(data.get("ingredient_data_status"), "PARTIAL"),
            "now": now,
        }
        db.execute_write(query, params)
        # Relationships are created separately so an empty list in one kind never
        # short-circuits the others (UNWIND [] yields zero rows and ends the query).
        self._set_relationships(
            dish_id,
            restaurant_ids=restaurant_ids or [],
            ingredient_ids=ingredient_ids or [],
            may_contain_allergen_ids=may_contain_allergen_ids or [],
        )
        return self.get_by_id(dish_id)

    def update(self, dish_id: str, data: Dict[str, Any], restaurant_ids: Optional[List[str]] = None, ingredient_ids: Optional[List[str]] = None, may_contain_allergen_ids: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        now = self._now_iso()
        set_statements = ["d.updated_at = $now"]
        params: Dict[str, Any] = {"id": dish_id, "now": now}

        field_map = {
            "name": str,
            "description": str,
            "category": str,
            "price": float,
            "vegetarian": bool,
            "vegan": bool,
            "preparation_notes": str,
            "availability_status": str,
            "ingredient_data_status": str
        }

        for field, field_type in field_map.items():
            if field in data and data[field] is not None:
                set_statements.append(f"d.{field} = ${field}")
                val = data[field]
                if field_type == str and isinstance(val, str):
                    params[field] = val.strip()
                elif field_type == float:
                    params[field] = float(val)
                elif field_type == bool:
                    params[field] = bool(val)
                else:
                    params[field] = val

        # 1. Update dish properties
        update_query = f"""
        MATCH (d:Dish {{id: $id}})
        SET {', '.join(set_statements)}
        RETURN d.id as id
        """
        updated = db.execute_write(update_query, params)
        if not updated:
            return None

        # 2. Update relationships if provided (None = leave untouched)
        self._set_relationships(
            dish_id,
            restaurant_ids=restaurant_ids,
            ingredient_ids=ingredient_ids,
            may_contain_allergen_ids=may_contain_allergen_ids,
        )

        return self.get_by_id(dish_id)

    def delete(self, dish_id: str) -> bool:
        query = """
        MATCH (d:Dish {id: $id})
        DETACH DELETE d
        RETURN count(d) as count
        """
        record = db.execute_single(query, {"id": dish_id})
        return record["count"] > 0 if record else False

    def list_dishes(self, skip: int = 0, limit: int = 20, search: Optional[str] = None, restaurant_id: Optional[str] = None, category: Optional[str] = None, allergen_id: Optional[str] = None, availability: Optional[str] = None) -> List[Dict[str, Any]]:
        where_clauses = ["1=1"]
        params: Dict[str, Any] = {"skip": skip, "limit": limit}

        if search:
            where_clauses.append("(toLower(d.name) CONTAINS toLower($search) OR toLower(d.description) CONTAINS toLower($search) OR toLower(d.category) CONTAINS toLower($search))")
            params["search"] = search.strip()
        if category:
            where_clauses.append("toLower(d.category) = toLower($category)")
            params["category"] = category.strip()
        if availability:
            where_clauses.append("d.availability_status = $availability")
            params["availability"] = availability.strip()
        if restaurant_id:
            where_clauses.append("EXISTS { MATCH (r_filter:Restaurant {id: $restaurant_id})-[:OFFERS]->(d) }")
            params["restaurant_id"] = restaurant_id.strip()
        if allergen_id:
            where_clauses.append("""(
                EXISTS { MATCH (d)-[:CONTAINS]->(:Ingredient)-[:CONTAINS_ALLERGEN]->(a_filter:Allergen {id: $allergen_id}) }
                OR EXISTS { MATCH (d)-[:MAY_CONTAIN]->(a_filter2:Allergen {id: $allergen_id}) }
            )""")
            params["allergen_id"] = allergen_id.strip()

        query = f"""
        MATCH (d:Dish)
        WHERE {' AND '.join(where_clauses)}
        OPTIONAL MATCH (r:Restaurant)-[:OFFERS]->(d)
        OPTIONAL MATCH (d)-[:CONTAINS]->(i:Ingredient)
        OPTIONAL MATCH (i)-[:CONTAINS_ALLERGEN]->(ia:Allergen)
        OPTIONAL MATCH (d)-[:MAY_CONTAIN]->(mca:Allergen)
        WITH d,
             collect(DISTINCT {{id: r.id, name: r.name, city: r.city}}) as restaurants,
             count(DISTINCT i) as ingredient_count,
             collect(DISTINCT {{id: ia.id, name: ia.name, allergen_category: ia.allergen_category}}) as allergens,
             collect(DISTINCT {{id: mca.id, name: mca.name, allergen_category: mca.allergen_category}}) as may_contain_allergens
        RETURN d, restaurants, ingredient_count, allergens, may_contain_allergens
        ORDER BY d.name ASC
        SKIP $skip
        LIMIT $limit
        """
        records = db.execute_query(query, params)
        results = []
        for rec in records:
            dish = dict(rec["d"])
            dish["restaurants"] = [r for r in rec["restaurants"] if r.get("id")]
            dish["ingredient_count"] = rec["ingredient_count"]
            dish["allergens"] = [a for a in rec["allergens"] if a.get("id")]
            dish["may_contain_allergens"] = [m for m in rec["may_contain_allergens"] if m.get("id")]
            results.append(dish)
        return results

    def count_dishes(self, search: Optional[str] = None, restaurant_id: Optional[str] = None, category: Optional[str] = None, allergen_id: Optional[str] = None, availability: Optional[str] = None) -> int:
        where_clauses = ["1=1"]
        params: Dict[str, Any] = {}

        if search:
            where_clauses.append("(toLower(d.name) CONTAINS toLower($search) OR toLower(d.description) CONTAINS toLower($search) OR toLower(d.category) CONTAINS toLower($search))")
            params["search"] = search.strip()
        if category:
            where_clauses.append("toLower(d.category) = toLower($category)")
            params["category"] = category.strip()
        if availability:
            where_clauses.append("d.availability_status = $availability")
            params["availability"] = availability.strip()
        if restaurant_id:
            where_clauses.append("EXISTS { MATCH (r_filter:Restaurant {id: $restaurant_id})-[:OFFERS]->(d) }")
            params["restaurant_id"] = restaurant_id.strip()
        if allergen_id:
            where_clauses.append("""(
                EXISTS { MATCH (d)-[:CONTAINS]->(:Ingredient)-[:CONTAINS_ALLERGEN]->(a_filter:Allergen {id: $allergen_id}) }
                OR EXISTS { MATCH (d)-[:MAY_CONTAIN]->(a_filter2:Allergen {id: $allergen_id}) }
            )""")
            params["allergen_id"] = allergen_id.strip()

        query = f"""
        MATCH (d:Dish)
        WHERE {' AND '.join(where_clauses)}
        RETURN count(d) as count
        """
        record = db.execute_single(query, params)
        return record["count"] if record else 0

    def get_distinct_categories(self) -> List[str]:
        query = """
        MATCH (d:Dish)
        WHERE d.category IS NOT NULL AND d.category <> ''
        RETURN DISTINCT d.category as category
        ORDER BY category ASC
        """
        records = db.execute_query(query)
        return [r["category"] for r in records]

dish_repo = DishRepository()
