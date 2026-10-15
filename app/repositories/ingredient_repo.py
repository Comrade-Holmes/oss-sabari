import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from app.database import db

class IngredientRepository:
    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def get_by_id(self, ingredient_id: str) -> Optional[Dict[str, Any]]:
        query = """
        MATCH (i:Ingredient {id: $id})
        OPTIONAL MATCH (i)-[:CONTAINS_ALLERGEN]->(a:Allergen)
        OPTIONAL MATCH (d:Dish)-[:CONTAINS]->(i)
        OPTIONAL MATCH (r:Restaurant)-[:OFFERS]->(d)
        WITH i,
             collect(DISTINCT {id: a.id, name: a.name, allergen_category: a.allergen_category}) as allergens,
             collect(DISTINCT {id: d.id, name: d.name, category: d.category}) as dishes,
             collect(DISTINCT {id: r.id, name: r.name, city: r.city}) as restaurants
        RETURN i, allergens, dishes, restaurants
        LIMIT 1
        """
        record = db.execute_single(query, {"id": ingredient_id})
        if not record or not record.get("i"):
            return None
        ing = dict(record["i"])
        ing["allergens"] = [a for a in record["allergens"] if a.get("id")]
        ing["dishes"] = [d for d in record["dishes"] if d.get("id")]
        ing["restaurants"] = [r for r in record["restaurants"] if r.get("id")]
        ing["dish_count"] = len(ing["dishes"])
        return ing

    def _set_allergens(self, ingredient_id: str, allergen_ids: List[str]) -> None:
        """Replace the ingredient's CONTAINS_ALLERGEN links atomically."""
        ids: List[str] = []
        for x in allergen_ids or []:
            x = str(x).strip()
            if x and x not in ids:
                ids.append(x)
        with db.get_session() as session:
            def _tx(tx):
                tx.run(
                    "MATCH (i:Ingredient {id: $id})-[rel:CONTAINS_ALLERGEN]->(:Allergen) DELETE rel",
                    {"id": ingredient_id},
                ).consume()
                if ids:
                    tx.run(
                        """
                        MATCH (i:Ingredient {id: $id})
                        UNWIND $ids AS a_id
                        MATCH (a:Allergen {id: a_id})
                        MERGE (i)-[:CONTAINS_ALLERGEN]->(a)
                        """,
                        {"id": ingredient_id, "ids": ids},
                    ).consume()
            session.execute_write(_tx)

    @staticmethod
    def _txt(value: Any, default: str = "") -> str:
        if value is None:
            return default
        value = getattr(value, "value", value)  # Enum -> plain value
        return str(value).strip()

    def create(self, data: Dict[str, Any], allergen_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        ingredient_id = str(uuid.uuid4())
        now = self._now_iso()
        v_status = self._txt(data.get("verification_status"), "UNVERIFIED")
        last_verified = now if v_status == "VERIFIED" else None

        query = """
        CREATE (i:Ingredient {
            id: $id,
            name: $name,
            description: $description,
            category: $category,
            verification_status: $verification_status,
            source_reference: $source_reference,
            last_verified_at: $last_verified_at,
            created_at: $now,
            updated_at: $now
        })
        RETURN i.id as id
        """
        params = {
            "id": ingredient_id,
            "name": self._txt(data.get("name")),
            "description": self._txt(data.get("description")),
            "category": self._txt(data.get("category"), "General"),
            "verification_status": v_status,
            "source_reference": self._txt(data.get("source_reference")),
            "last_verified_at": last_verified,
            "now": now,
        }
        db.execute_write(query, params)
        if allergen_ids:
            self._set_allergens(ingredient_id, allergen_ids)
        return self.get_by_id(ingredient_id)

    def update(self, ingredient_id: str, data: Dict[str, Any], allergen_ids: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        now = self._now_iso()
        set_statements = ["i.updated_at = $now"]
        params: Dict[str, Any] = {"id": ingredient_id, "now": now}

        fields = ["name", "description", "category", "verification_status", "source_reference"]
        for field in fields:
            if field in data and data[field] is not None:
                params[field] = self._txt(data[field])
                set_statements.append(f"i.{field} = ${field}")
                if field == "verification_status" and params[field] == "VERIFIED":
                    set_statements.append("i.last_verified_at = $now")

        update_query = f"""
        MATCH (i:Ingredient {{id: $id}})
        SET {', '.join(set_statements)}
        RETURN i.id as id
        """
        if not db.execute_write(update_query, params):
            return None  # ingredient does not exist

        if allergen_ids is not None:
            self._set_allergens(ingredient_id, allergen_ids)

        return self.get_by_id(ingredient_id)

    def delete(self, ingredient_id: str) -> bool:
        query = """
        MATCH (i:Ingredient {id: $id})
        DETACH DELETE i
        RETURN count(i) as count
        """
        record = db.execute_single(query, {"id": ingredient_id})
        return record["count"] > 0 if record else False

    def list_ingredients(self, skip: int = 0, limit: int = 20, search: Optional[str] = None, category: Optional[str] = None, verification_status: Optional[str] = None, allergen_id: Optional[str] = None) -> List[Dict[str, Any]]:
        where_clauses = ["1=1"]
        params: Dict[str, Any] = {"skip": skip, "limit": limit}

        if search:
            where_clauses.append("(toLower(i.name) CONTAINS toLower($search) OR toLower(i.description) CONTAINS toLower($search) OR toLower(i.category) CONTAINS toLower($search))")
            params["search"] = search.strip()
        if category:
            where_clauses.append("toLower(i.category) = toLower($category)")
            params["category"] = category.strip()
        if verification_status:
            where_clauses.append("i.verification_status = $verification_status")
            params["verification_status"] = verification_status.strip()
        if allergen_id:
            where_clauses.append("EXISTS { MATCH (i)-[:CONTAINS_ALLERGEN]->(a:Allergen {id: $allergen_id}) }")
            params["allergen_id"] = allergen_id.strip()

        query = f"""
        MATCH (i:Ingredient)
        WHERE {' AND '.join(where_clauses)}
        OPTIONAL MATCH (i)-[:CONTAINS_ALLERGEN]->(a:Allergen)
        OPTIONAL MATCH (d:Dish)-[:CONTAINS]->(i)
        WITH i,
             collect(DISTINCT {{id: a.id, name: a.name, allergen_category: a.allergen_category}}) as allergens,
             count(DISTINCT d) as dish_count
        RETURN i, allergens, dish_count
        ORDER BY i.name ASC
        SKIP $skip
        LIMIT $limit
        """
        records = db.execute_query(query, params)
        results = []
        for rec in records:
            ing = dict(rec["i"])
            ing["allergens"] = [a for a in rec["allergens"] if a.get("id")]
            ing["dish_count"] = rec["dish_count"]
            results.append(ing)
        return results

    def count_ingredients(self, search: Optional[str] = None, category: Optional[str] = None, verification_status: Optional[str] = None, allergen_id: Optional[str] = None) -> int:
        where_clauses = ["1=1"]
        params: Dict[str, Any] = {}

        if search:
            where_clauses.append("(toLower(i.name) CONTAINS toLower($search) OR toLower(i.description) CONTAINS toLower($search) OR toLower(i.category) CONTAINS toLower($search))")
            params["search"] = search.strip()
        if category:
            where_clauses.append("toLower(i.category) = toLower($category)")
            params["category"] = category.strip()
        if verification_status:
            where_clauses.append("i.verification_status = $verification_status")
            params["verification_status"] = verification_status.strip()
        if allergen_id:
            where_clauses.append("EXISTS { MATCH (i)-[:CONTAINS_ALLERGEN]->(a:Allergen {id: $allergen_id}) }")
            params["allergen_id"] = allergen_id.strip()

        query = f"""
        MATCH (i:Ingredient)
        WHERE {' AND '.join(where_clauses)}
        RETURN count(i) as count
        """
        record = db.execute_single(query, params)
        return record["count"] if record else 0

    def get_distinct_categories(self) -> List[str]:
        query = """
        MATCH (i:Ingredient)
        WHERE i.category IS NOT NULL AND i.category <> ''
        RETURN DISTINCT i.category as category
        ORDER BY category ASC
        """
        records = db.execute_query(query)
        return [r["category"] for r in records]

ingredient_repo = IngredientRepository()
