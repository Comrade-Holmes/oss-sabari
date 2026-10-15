import csv
import io
from typing import Any, Dict, List
from app.database import db

class ReportsRepository:
    def get_dashboard_stats(self) -> Dict[str, Any]:
        counts_query = """
        MATCH (r:Restaurant) WITH count(r) as total_restaurants
        MATCH (d:Dish) WITH total_restaurants, count(d) as total_dishes
        MATCH (i:Ingredient) WITH total_restaurants, total_dishes, count(i) as total_ingredients
        MATCH (a:Allergen) WITH total_restaurants, total_dishes, total_ingredients, count(a) as total_allergens
        MATCH (u:User) WITH total_restaurants, total_dishes, total_ingredients, total_allergens, count(u) as total_users
        RETURN total_restaurants, total_dishes, total_ingredients, total_allergens, total_users
        """
        counts = db.execute_single(counts_query) or {
            "total_restaurants": 0,
            "total_dishes": 0,
            "total_ingredients": 0,
            "total_allergens": 0,
            "total_users": 0
        }

        # Count dishes with potential allergen matches
        allergen_matches_query = """
        MATCH (d:Dish)
        WHERE EXISTS { MATCH (d)-[:CONTAINS]->(:Ingredient)-[:CONTAINS_ALLERGEN]->(:Allergen) }
           OR EXISTS { MATCH (d)-[:MAY_CONTAIN]->(:Allergen) }
        RETURN count(DISTINCT d) as count
        """
        allergen_match_rec = db.execute_single(allergen_matches_query)
        counts["dishes_with_allergens"] = allergen_match_rec["count"] if allergen_match_rec else 0

        # Count unverified ingredients
        unverified_query = """
        MATCH (i:Ingredient)
        WHERE i.verification_status <> 'VERIFIED' OR i.verification_status IS NULL
        RETURN count(i) as count
        """
        unverified_rec = db.execute_single(unverified_query)
        counts["unverified_ingredients"] = unverified_rec["count"] if unverified_rec else 0

        # Count incomplete dishes
        incomplete_dishes_query = """
        MATCH (d:Dish)
        WHERE d.ingredient_data_status <> 'COMPLETE' OR NOT EXISTS { MATCH (d)-[:CONTAINS]->(:Ingredient) }
        RETURN count(d) as count
        """
        incomplete_rec = db.execute_single(incomplete_dishes_query)
        counts["incomplete_dishes"] = incomplete_rec["count"] if incomplete_rec else 0

        return counts

    def get_allergen_distribution(self) -> List[Dict[str, Any]]:
        query = """
        MATCH (a:Allergen)
        OPTIONAL MATCH (i:Ingredient)-[:CONTAINS_ALLERGEN]->(a)
        OPTIONAL MATCH (d:Dish)-[:CONTAINS]->(i)
        OPTIONAL MATCH (d2:Dish)-[:MAY_CONTAIN]->(a)
        RETURN 
            a.name as allergen_name,
            count(DISTINCT i) as ingredient_count,
            count(DISTINCT d) + count(DISTINCT d2) as dish_count
        ORDER BY dish_count DESC, ingredient_count DESC
        LIMIT 10
        """
        return db.execute_query(query)

    def get_restaurant_dish_distribution(self) -> List[Dict[str, Any]]:
        query = """
        MATCH (r:Restaurant)
        OPTIONAL MATCH (r)-[:OFFERS]->(d:Dish)
        RETURN 
            r.name as restaurant_name,
            r.city as city,
            count(d) as dish_count
        ORDER BY dish_count DESC
        LIMIT 10
        """
        return db.execute_query(query)

    def get_verification_status_breakdown(self) -> Dict[str, int]:
        query = """
        MATCH (i:Ingredient)
        RETURN 
            coalesce(i.verification_status, 'UNVERIFIED') as status,
            count(i) as count
        """
        records = db.execute_query(query)
        breakdown = {"VERIFIED": 0, "UNVERIFIED": 0, "IN_REVIEW": 0}
        for rec in records:
            breakdown[rec["status"]] = rec["count"]
        return breakdown

    # Alias for convenience
    get_verification_breakdown = get_verification_status_breakdown

    def get_unverified_ingredients_report(self) -> List[Dict[str, Any]]:
        query = """
        MATCH (i:Ingredient)
        WHERE i.verification_status <> 'VERIFIED' OR i.verification_status IS NULL
        OPTIONAL MATCH (d:Dish)-[:CONTAINS]->(i)
        OPTIONAL MATCH (r:Restaurant)-[:OFFERS]->(d)
        RETURN 
            i.id as id,
            i.name as name,
            i.category as category,
            coalesce(i.verification_status, 'UNVERIFIED') as status,
            coalesce(i.source_reference, 'None') as source,
            count(DISTINCT d) as affected_dishes,
            count(DISTINCT r) as affected_restaurants
        ORDER BY affected_dishes DESC, i.name ASC
        """
        return db.execute_query(query)

    def get_incomplete_dishes_report(self) -> List[Dict[str, Any]]:
        query = """
        MATCH (d:Dish)
        OPTIONAL MATCH (r:Restaurant)-[:OFFERS]->(d)
        OPTIONAL MATCH (d)-[:CONTAINS]->(i:Ingredient)
        WITH d, r, count(i) as ingredient_count
        WHERE d.ingredient_data_status <> 'COMPLETE' OR ingredient_count = 0
        RETURN 
            d.id as id,
            d.name as name,
            d.category as category,
            coalesce(d.ingredient_data_status, 'PARTIAL') as data_status,
            r.name as restaurant_name,
            r.city as city,
            ingredient_count
        ORDER BY d.name ASC
        """
        return db.execute_query(query)

    def get_data_quality_issues(self) -> List[Dict[str, Any]]:
        issues = []

        # Check 1: Dishes with 0 ingredients
        q1 = """
        MATCH (d:Dish)
        WHERE NOT EXISTS { MATCH (d)-[:CONTAINS]->(:Ingredient) }
        OPTIONAL MATCH (r:Restaurant)-[:OFFERS]->(d)
        RETURN d.name as name, d.id as id, r.name as restaurant, 'Dish has zero recorded ingredients' as issue, 'HIGH' as severity
        LIMIT 20
        """
        for r in db.execute_query(q1):
            issues.append(r)

        # Check 2: Unverified ingredients used in available dishes
        q2 = """
        MATCH (d:Dish {availability_status: 'AVAILABLE'})-[:CONTAINS]->(i:Ingredient)
        WHERE i.verification_status <> 'VERIFIED'
        RETURN i.name as name, i.id as id, d.name as dish, 'Unverified ingredient active in menu dish' as issue, 'MEDIUM' as severity
        LIMIT 20
        """
        for r in db.execute_query(q2):
            issues.append(r)

        # Check 3: Ingredients with no allergen connections recorded
        q3 = """
        MATCH (i:Ingredient)
        WHERE NOT EXISTS { MATCH (i)-[:CONTAINS_ALLERGEN]->(:Allergen) }
        RETURN i.name as name, i.id as id, 'General' as category, 'Ingredient has no allergen assessment linked' as issue, 'LOW' as severity
        LIMIT 20
        """
        for r in db.execute_query(q3):
            issues.append(r)

        return issues

    def export_csv(self, report_type: str) -> str:
        output = io.StringIO()
        writer = csv.writer(output)

        if report_type == "unverified_ingredients":
            data = self.get_unverified_ingredients_report()
            writer.writerow(["Ingredient Name", "Category", "Verification Status", "Source Reference", "Affected Dishes", "Affected Restaurants"])
            for row in data:
                writer.writerow([
                    row.get("name"),
                    row.get("category"),
                    row.get("status"),
                    row.get("source"),
                    row.get("affected_dishes"),
                    row.get("affected_restaurants")
                ])

        elif report_type == "incomplete_dishes":
            data = self.get_incomplete_dishes_report()
            writer.writerow(["Dish Name", "Category", "Data Status", "Restaurant", "City", "Recorded Ingredients Count"])
            for row in data:
                writer.writerow([
                    row.get("name"),
                    row.get("category"),
                    row.get("data_status"),
                    row.get("restaurant_name"),
                    row.get("city"),
                    row.get("ingredient_count")
                ])

        elif report_type == "allergen_distribution":
            data = self.get_allergen_distribution()
            writer.writerow(["Allergen Name", "Associated Ingredients Count", "Associated Dishes Count"])
            for row in data:
                writer.writerow([
                    row.get("allergen_name"),
                    row.get("ingredient_count"),
                    row.get("dish_count")
                ])

        elif report_type == "data_quality":
            data = self.get_data_quality_issues()
            writer.writerow(["Entity Name", "Issue Description", "Severity"])
            for row in data:
                writer.writerow([
                    row.get("name"),
                    row.get("issue"),
                    row.get("severity")
                ])

        return output.getvalue()

    def get_top_allergen_restaurants(self, limit: int = 10) -> List[Dict[str, Any]]:
        query = """
        MATCH (r:Restaurant)-[:OFFERS]->(d:Dish)
        OPTIONAL MATCH (d)-[:CONTAINS]->(:Ingredient)-[:CONTAINS_ALLERGEN]->(a1:Allergen)
        OPTIONAL MATCH (d)-[:MAY_CONTAIN]->(a2:Allergen)
        WITH r,
             count(DISTINCT a1) + count(DISTINCT a2) as allergen_variety,
             count(DISTINCT d) as dish_count
        RETURN
            r.id as id,
            r.name as restaurant_name,
            r.city as city,
            r.cuisine_type as cuisine_type,
            dish_count,
            allergen_variety
        ORDER BY allergen_variety DESC
        LIMIT $limit
        """
        return db.execute_query(query, {"limit": limit})

reports_repo = ReportsRepository()

