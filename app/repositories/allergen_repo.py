import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from app.database import db

class AllergenRepository:
    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def get_by_id(self, allergen_id: str) -> Optional[Dict[str, Any]]:
        query = """
        MATCH (a:Allergen {id: $id})
        OPTIONAL MATCH (i:Ingredient)-[:CONTAINS_ALLERGEN]->(a)
        OPTIONAL MATCH (d:Dish)-[:CONTAINS]->(i)
        OPTIONAL MATCH (d2:Dish)-[:MAY_CONTAIN]->(a)
        OPTIONAL MATCH (r:Restaurant)-[:OFFERS]->(d)
        WITH a,
             count(DISTINCT i) as ingredient_count,
             count(DISTINCT d) + count(DISTINCT d2) as dish_count,
             count(DISTINCT r) as restaurant_count
        RETURN a, ingredient_count, dish_count, restaurant_count
        LIMIT 1
        """
        record = db.execute_single(query, {"id": allergen_id})
        if not record or not record.get("a"):
            return None
        item = dict(record["a"])
        item["ingredient_count"] = record["ingredient_count"]
        item["dish_count"] = record["dish_count"]
        item["restaurant_count"] = record["restaurant_count"]
        return item

    def get_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        query = """
        MATCH (a:Allergen)
        WHERE toLower(a.name) = toLower($name)
        RETURN a
        LIMIT 1
        """
        record = db.execute_single(query, {"name": name.strip()})
        return record["a"] if record else None

    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        allergen_id = str(uuid.uuid4())
        now = self._now_iso()
        query = """
        CREATE (a:Allergen {
            id: $id,
            name: $name,
            description: $description,
            allergen_category: $allergen_category,
            created_at: $now,
            updated_at: $now
        })
        RETURN a
        """
        params = {
            "id": allergen_id,
            "name": data.get("name", "").strip(),
            "description": data.get("description", "").strip(),
            "allergen_category": data.get("allergen_category", "Major").strip(),
            "now": now
        }
        record = db.execute_single(query, params)
        item = dict(record["a"])
        item["ingredient_count"] = 0
        item["dish_count"] = 0
        return item

    def update(self, allergen_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        now = self._now_iso()
        set_statements = ["a.updated_at = $now"]
        params: Dict[str, Any] = {"id": allergen_id, "now": now}

        fields = ["name", "description", "allergen_category"]
        for field in fields:
            if field in data and data[field] is not None:
                set_statements.append(f"a.{field} = ${field}")
                params[field] = data[field].strip() if isinstance(data[field], str) else data[field]

        query = f"""
        MATCH (a:Allergen {{id: $id}})
        SET {', '.join(set_statements)}
        RETURN a
        """
        record = db.execute_single(query, params)
        return self.get_by_id(allergen_id) if record else None

    def delete(self, allergen_id: str) -> bool:
        # Detach relationships to ingredients and dishes, then delete allergen
        query = """
        MATCH (a:Allergen {id: $id})
        DETACH DELETE a
        RETURN count(a) as count
        """
        record = db.execute_single(query, {"id": allergen_id})
        return record["count"] > 0 if record else False

    def list_allergens(self, skip: int = 0, limit: int = 50, search: Optional[str] = None, category: Optional[str] = None) -> List[Dict[str, Any]]:
        where_clauses = ["1=1"]
        params: Dict[str, Any] = {"skip": skip, "limit": limit}

        if search:
            where_clauses.append("(toLower(a.name) CONTAINS toLower($search) OR toLower(a.description) CONTAINS toLower($search))")
            params["search"] = search.strip()
        if category:
            where_clauses.append("toLower(a.allergen_category) = toLower($category)")
            params["category"] = category.strip()

        query = f"""
        MATCH (a:Allergen)
        WHERE {' AND '.join(where_clauses)}
        OPTIONAL MATCH (i:Ingredient)-[:CONTAINS_ALLERGEN]->(a)
        OPTIONAL MATCH (d:Dish)-[:CONTAINS]->(i)
        OPTIONAL MATCH (d2:Dish)-[:MAY_CONTAIN]->(a)
        WITH a,
             count(DISTINCT i) as ingredient_count,
             count(DISTINCT d) + count(DISTINCT d2) as dish_count
        RETURN a, ingredient_count, dish_count
        ORDER BY a.name ASC
        SKIP $skip
        LIMIT $limit
        """
        records = db.execute_query(query, params)
        results = []
        for rec in records:
            item = dict(rec["a"])
            item["ingredient_count"] = rec["ingredient_count"]
            item["dish_count"] = rec["dish_count"]
            results.append(item)
        return results

    def count_allergens(self, search: Optional[str] = None, category: Optional[str] = None) -> int:
        where_clauses = ["1=1"]
        params: Dict[str, Any] = {}

        if search:
            where_clauses.append("(toLower(a.name) CONTAINS toLower($search) OR toLower(a.description) CONTAINS toLower($search))")
            params["search"] = search.strip()
        if category:
            where_clauses.append("toLower(a.allergen_category) = toLower($category)")
            params["category"] = category.strip()

        query = f"""
        MATCH (a:Allergen)
        WHERE {' AND '.join(where_clauses)}
        RETURN count(a) as count
        """
        record = db.execute_single(query, params)
        return record["count"] if record else 0

    def get_connected_dishes_and_restaurants(self, allergen_id: str) -> Dict[str, Any]:
        query = """
        MATCH (a:Allergen {id: $id})
        OPTIONAL MATCH (i:Ingredient)-[:CONTAINS_ALLERGEN]->(a)
        OPTIONAL MATCH (d:Dish)-[:CONTAINS]->(i)
        OPTIONAL MATCH (d2:Dish)-[:MAY_CONTAIN]->(a)
        WITH a, 
             collect(DISTINCT {id: i.id, name: i.name}) as ingredients,
             collect(DISTINCT {id: d.id, name: d.name, type: 'Direct Ingredient'}) + 
             collect(DISTINCT {id: d2.id, name: d2.name, type: 'Precautionary Cross-Contact'}) as dishes
        RETURN a, ingredients, dishes
        """
        record = db.execute_single(query, {"id": allergen_id})
        if not record:
            return {"ingredients": [], "dishes": []}
        return {
            "ingredients": [i for i in record["ingredients"] if i.get("id")],
            "dishes": [d for d in record["dishes"] if d.get("id")]
        }

    def get_distinct_categories(self) -> List[str]:
        query = """
        MATCH (a:Allergen)
        WHERE a.allergen_category IS NOT NULL AND a.allergen_category <> ''
        RETURN DISTINCT a.allergen_category as category
        ORDER BY category ASC
        """
        records = db.execute_query(query)
        return [r["category"] for r in records]

allergen_repo = AllergenRepository()
