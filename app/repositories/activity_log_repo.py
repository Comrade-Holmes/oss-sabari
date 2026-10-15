import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from app.database import db

class ActivityLogRepository:
    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def log(
        self,
        action: str,
        entity_type: str,
        entity_id: str,
        # Accept either naming convention used across routers
        actor_id: str = "",
        actor_name: str = "",
        description: str = "",
        # Aliases used in some routers
        user_id: str = "",
        user_name: str = "",
        details: str = "",
    ) -> Dict[str, Any]:
        # Normalise parameter aliases
        _actor_id = actor_id or user_id
        _actor_name = actor_name or user_name
        _description = description or details

        log_id = str(uuid.uuid4())
        now = self._now_iso()

        query = """
        MATCH (u:User {id: $actor_id})
        CREATE (al:ActivityLog {
            id: $id,
            actor_id: $actor_id,
            actor_name: $actor_name,
            action: $action,
            entity_type: $entity_type,
            entity_id: $entity_id,
            description: $description,
            timestamp: $now
        })
        CREATE (u)-[:PERFORMED]->(al)
        RETURN al
        """
        params = {
            "id": log_id,
            "actor_id": _actor_id,
            "actor_name": _actor_name,
            "action": action.upper(),
            "entity_type": entity_type.capitalize(),
            "entity_id": str(entity_id),
            "description": _description,
            "now": now
        }
        record = db.execute_single(query, params)
        if not record:
            # Fallback if user node wasn't found by ID
            fallback_query = """
            CREATE (al:ActivityLog {
                id: $id,
                actor_id: $actor_id,
                actor_name: $actor_name,
                action: $action,
                entity_type: $entity_type,
                entity_id: $entity_id,
                description: $description,
                timestamp: $now
            })
            RETURN al
            """
            record = db.execute_single(fallback_query, params)

        return record["al"] if record else {}

    def list_logs(
        self,
        skip: int = 0,
        limit: int = 25,
        entity_type: Optional[str] = None,
        action: Optional[str] = None,
        actor_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        where_clauses = ["1=1"]
        params: Dict[str, Any] = {"skip": skip, "limit": limit}

        _actor = actor_id or user_id
        if _actor:
            where_clauses.append("al.actor_id = $actor_id")
            params["actor_id"] = _actor.strip()
        if entity_type:
            where_clauses.append("toLower(al.entity_type) = toLower($entity_type)")
            params["entity_type"] = entity_type.strip()
        if action:
            where_clauses.append("toLower(al.action) = toLower($action)")
            params["action"] = action.strip()

        query = f"""
        MATCH (al:ActivityLog)
        WHERE {' AND '.join(where_clauses)}
        RETURN al
        ORDER BY al.timestamp DESC
        SKIP $skip
        LIMIT $limit
        """
        records = db.execute_query(query, params)
        return [r["al"] for r in records]

    def count_logs(
        self,
        entity_type: Optional[str] = None,
        action: Optional[str] = None,
        actor_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> int:
        where_clauses = ["1=1"]
        params: Dict[str, Any] = {}

        _actor = actor_id or user_id
        if _actor:
            where_clauses.append("al.actor_id = $actor_id")
            params["actor_id"] = _actor.strip()
        if entity_type:
            where_clauses.append("toLower(al.entity_type) = toLower($entity_type)")
            params["entity_type"] = entity_type.strip()
        if action:
            where_clauses.append("toLower(al.action) = toLower($action)")
            params["action"] = action.strip()

        query = f"""
        MATCH (al:ActivityLog)
        WHERE {' AND '.join(where_clauses)}
        RETURN count(al) as count
        """
        record = db.execute_single(query, params)
        return record["count"] if record else 0

activity_log_repo = ActivityLogRepository()
