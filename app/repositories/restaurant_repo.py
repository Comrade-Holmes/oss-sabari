import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from app.database import db

class RestaurantRepository:
    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def get_by_id(self, restaurant_id: str) -> Optional[Dict[str, Any]]:
        query = """
        MATCH (r:Restaurant {id: $id})
        OPTIONAL MATCH (r)-[:OFFERS]->(d:Dish)
        RETURN r, count(d) as dish_count
        """
        record = db.execute_single(query, {"id": restaurant_id})
        if not record or not record.get("r"):
            return None
        res = dict(record["r"])
        res["dish_count"] = record["dish_count"]
        return res

    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        restaurant_id = str(uuid.uuid4())
        now = self._now_iso()
        query = """
        CREATE (r:Restaurant {
            id: $id,
            name: $name,
            description: $description,
            address: $address,
            city: $city,
            phone: $phone,
            email: $email,
            cuisine_type: $cuisine_type,
            status: $status,
            created_at: $now,
            updated_at: $now
        })
        RETURN r
        """
        params = {
            "id": restaurant_id,
            "name": data.get("name", "").strip(),
            "description": data.get("description", "").strip(),
            "address": data.get("address", "").strip(),
            "city": data.get("city", "").strip(),
            "phone": data.get("phone", "").strip(),
            "email": data.get("email", "").strip(),
            "cuisine_type": data.get("cuisine_type", "Various").strip(),
            "status": data.get("status", "ACTIVE").strip(),
            "now": now
        }
        record = db.execute_single(query, params)
        res = dict(record["r"])
        res["dish_count"] = 0
        return res

    def update(self, restaurant_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        now = self._now_iso()
        set_statements = ["r.updated_at = $now"]
        params: Dict[str, Any] = {"id": restaurant_id, "now": now}

        fields = ["name", "description", "address", "city", "phone", "email", "cuisine_type", "status"]
        for field in fields:
            if field in data and data[field] is not None:
                set_statements.append(f"r.{field} = ${field}")
                params[field] = data[field].strip() if isinstance(data[field], str) else data[field]

        query = f"""
        MATCH (r:Restaurant {{id: $id}})
        SET {', '.join(set_statements)}
        WITH r
        OPTIONAL MATCH (r)-[:OFFERS]->(d:Dish)
        RETURN r, count(d) as dish_count
        """
        record = db.execute_single(query, params)
        if not record or not record.get("r"):
            return None
        res = dict(record["r"])
        res["dish_count"] = record["dish_count"]
        return res

    def delete(self, restaurant_id: str) -> bool:
        # Detach restaurant relations and delete node, without deleting the Dishes it offered
        query = """
        MATCH (r:Restaurant {id: $id})
        DETACH DELETE r
        RETURN count(r) as count
        """
        record = db.execute_single(query, {"id": restaurant_id})
        return record["count"] > 0 if record else False

    def list_restaurants(self, skip: int = 0, limit: int = 20, search: Optional[str] = None, city: Optional[str] = None, cuisine: Optional[str] = None, status: Optional[str] = None) -> List[Dict[str, Any]]:
        where_clauses = ["1=1"]
        params: Dict[str, Any] = {"skip": skip, "limit": limit}

        if search:
            where_clauses.append("(toLower(r.name) CONTAINS toLower($search) OR toLower(r.city) CONTAINS toLower($search) OR toLower(r.cuisine_type) CONTAINS toLower($search))")
            params["search"] = search.strip()
        if city:
            where_clauses.append("toLower(r.city) = toLower($city)")
            params["city"] = city.strip()
        if cuisine:
            where_clauses.append("toLower(r.cuisine_type) = toLower($cuisine)")
            params["cuisine"] = cuisine.strip()
        if status:
            where_clauses.append("r.status = $status")
            params["status"] = status.strip()

        query = f"""
        MATCH (r:Restaurant)
        WHERE {' AND '.join(where_clauses)}
        OPTIONAL MATCH (r)-[:OFFERS]->(d:Dish)
        RETURN r, count(d) as dish_count
        ORDER BY r.name ASC
        SKIP $skip
        LIMIT $limit
        """
        records = db.execute_query(query, params)
        results = []
        for rec in records:
            item = dict(rec["r"])
            item["dish_count"] = rec["dish_count"]
            results.append(item)
        return results

    def count_restaurants(self, search: Optional[str] = None, city: Optional[str] = None, cuisine: Optional[str] = None, status: Optional[str] = None) -> int:
        where_clauses = ["1=1"]
        params: Dict[str, Any] = {}

        if search:
            where_clauses.append("(toLower(r.name) CONTAINS toLower($search) OR toLower(r.city) CONTAINS toLower($search) OR toLower(r.cuisine_type) CONTAINS toLower($search))")
            params["search"] = search.strip()
        if city:
            where_clauses.append("toLower(r.city) = toLower($city)")
            params["city"] = city.strip()
        if cuisine:
            where_clauses.append("toLower(r.cuisine_type) = toLower($cuisine)")
            params["cuisine"] = cuisine.strip()
        if status:
            where_clauses.append("r.status = $status")
            params["status"] = status.strip()

        query = f"""
        MATCH (r:Restaurant)
        WHERE {' AND '.join(where_clauses)}
        RETURN count(r) as count
        """
        record = db.execute_single(query, params)
        return record["count"] if record else 0

    def get_distinct_cities(self) -> List[str]:
        query = """
        MATCH (r:Restaurant)
        WHERE r.city IS NOT NULL AND r.city <> ''
        RETURN DISTINCT r.city as city
        ORDER BY city ASC
        """
        records = db.execute_query(query)
        return [r["city"] for r in records]

    def get_distinct_cuisines(self) -> List[str]:
        query = """
        MATCH (r:Restaurant)
        WHERE r.cuisine_type IS NOT NULL AND r.cuisine_type <> ''
        RETURN DISTINCT r.cuisine_type as cuisine
        ORDER BY cuisine ASC
        """
        records = db.execute_query(query)
        return [r["cuisine"] for r in records]

    def get_restaurant_dishes(self, restaurant_id: str) -> List[Dict[str, Any]]:
        query = """
        MATCH (r:Restaurant {id: $id})-[:OFFERS]->(d:Dish)
        OPTIONAL MATCH (d)-[:CONTAINS]->(i:Ingredient)-[:CONTAINS_ALLERGEN]->(a:Allergen)
        OPTIONAL MATCH (d)-[:MAY_CONTAIN]->(mca:Allergen)
        WITH d, 
             collect(DISTINCT {id: a.id, name: a.name, category: a.allergen_category}) as direct_allergens,
             collect(DISTINCT {id: mca.id, name: mca.name, category: mca.allergen_category}) as may_allergens
        RETURN d, direct_allergens, may_allergens
        ORDER BY d.name ASC
        """
        records = db.execute_query(query, {"id": restaurant_id})
        dishes = []
        for rec in records:
            dish = dict(rec["d"])
            dish["allergens"] = [a for a in rec["direct_allergens"] if a.get("id")]
            dish["may_contain_allergens"] = [m for m in rec["may_allergens"] if m.get("id")]
            dishes.append(dish)
        return dishes

restaurant_repo = RestaurantRepository()
