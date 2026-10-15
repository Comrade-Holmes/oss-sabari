import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from app.database import db

class UserRepository:
    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        query = """
        MATCH (u:User)
        WHERE toLower(u.email) = toLower($email)
        RETURN u
        LIMIT 1
        """
        record = db.execute_single(query, {"email": email.strip()})
        return record["u"] if record else None

    def get_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        query = """
        MATCH (u:User {id: $id})
        RETURN u
        LIMIT 1
        """
        record = db.execute_single(query, {"id": user_id})
        return record["u"] if record else None

    def create(self, full_name: str, email: str, password_hash: str, role: str = "VIEWER") -> Dict[str, Any]:
        user_id = str(uuid.uuid4())
        now = self._now_iso()
        query = """
        CREATE (u:User {
            id: $id,
            full_name: $full_name,
            email: toLower($email),
            password_hash: $password_hash,
            role: $role,
            is_active: true,
            created_at: $now,
            updated_at: $now
        })
        RETURN u
        """
        params = {
            "id": user_id,
            "full_name": full_name.strip(),
            "email": email.strip(),
            "password_hash": password_hash,
            "role": role.upper(),
            "now": now
        }
        record = db.execute_single(query, params)
        return record["u"]

    def update_profile(self, user_id: str, full_name: str) -> Optional[Dict[str, Any]]:
        now = self._now_iso()
        query = """
        MATCH (u:User {id: $id})
        SET u.full_name = $full_name,
            u.updated_at = $now
        RETURN u
        """
        record = db.execute_single(query, {"id": user_id, "full_name": full_name.strip(), "now": now})
        return record["u"] if record else None

    def update_password(self, user_id: str, new_hash: str) -> bool:
        now = self._now_iso()
        query = """
        MATCH (u:User {id: $id})
        SET u.password_hash = $new_hash,
            u.updated_at = $now
        RETURN count(u) as count
        """
        record = db.execute_single(query, {"id": user_id, "new_hash": new_hash, "now": now})
        return record["count"] > 0 if record else False

    def update_role(self, user_id: str, role: str) -> Optional[Dict[str, Any]]:
        now = self._now_iso()
        query = """
        MATCH (u:User {id: $id})
        SET u.role = $role,
            u.updated_at = $now
        RETURN u
        """
        record = db.execute_single(query, {"id": user_id, "role": role.upper(), "now": now})
        return record["u"] if record else None

    def update_status(self, user_id: str, is_active: bool) -> Optional[Dict[str, Any]]:
        now = self._now_iso()
        query = """
        MATCH (u:User {id: $id})
        SET u.is_active = $is_active,
            u.updated_at = $now
        RETURN u
        """
        record = db.execute_single(query, {"id": user_id, "is_active": is_active, "now": now})
        return record["u"] if record else None

    def count_active_admins(self) -> int:
        query = """
        MATCH (u:User)
        WHERE (toUpper(u.role) = 'ADMIN' OR u.role = 'admin') AND (u.is_active = true OR u.is_active IS NULL)
        RETURN count(u) as count
        """
        record = db.execute_single(query)
        return record["count"] if record else 0

    def list_users(self, skip: int = 0, limit: int = 20, search: Optional[str] = None, role: Optional[str] = None, is_active: Optional[bool] = None) -> List[Dict[str, Any]]:
        where_clauses = ["1=1"]
        params: Dict[str, Any] = {"skip": skip, "limit": limit}

        if search:
            where_clauses.append("(toLower(u.full_name) CONTAINS toLower($search) OR toLower(u.email) CONTAINS toLower($search))")
            params["search"] = search.strip()
        if role:
            where_clauses.append("toUpper(u.role) = toUpper($role)")
            params["role"] = role.strip()
        if is_active is not None:
            where_clauses.append("u.is_active = $is_active")
            params["is_active"] = is_active

        query = f"""
        MATCH (u:User)
        WHERE {' AND '.join(where_clauses)}
        RETURN u
        ORDER BY u.created_at DESC
        SKIP $skip
        LIMIT $limit
        """
        records = db.execute_query(query, params)
        return [r["u"] for r in records]

    def count_users(self, search: Optional[str] = None, role: Optional[str] = None, is_active: Optional[bool] = None) -> int:
        where_clauses = ["1=1"]
        params: Dict[str, Any] = {}

        if search:
            where_clauses.append("(toLower(u.full_name) CONTAINS toLower($search) OR toLower(u.email) CONTAINS toLower($search))")
            params["search"] = search.strip()
        if role:
            where_clauses.append("toUpper(u.role) = toUpper($role)")
            params["role"] = role.strip()
        if is_active is not None:
            where_clauses.append("u.is_active = $is_active")
            params["is_active"] = is_active

        query = f"""
        MATCH (u:User)
        WHERE {' AND '.join(where_clauses)}
        RETURN count(u) as count
        """
        record = db.execute_single(query, params)
        return record["count"] if record else 0

user_repo = UserRepository()
