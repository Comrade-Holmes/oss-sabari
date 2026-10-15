import logging
from contextlib import contextmanager
from typing import Any, Dict, List, Optional
from neo4j import GraphDatabase, Driver, Session
from app.config import settings

logger = logging.getLogger("allergraph.database")

class Database:
    def __init__(self):
        self._driver: Optional[Driver] = None

    def connect(self) -> Driver:
        if self._driver is None:
            logger.info(f"Connecting to Neo4j at {settings.NEO4J_URI}...")
            self._driver = GraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD),
                max_connection_lifetime=30 * 60,
                max_connection_pool_size=50,
                connection_acquisition_timeout=10.0
            )
            self.verify_connectivity()
        return self._driver

    def verify_connectivity(self) -> bool:
        if self._driver is None:
            self.connect()
        try:
            self._driver.verify_connectivity()
            logger.info("Successfully connected and verified Neo4j connection.")
            return True
        except Exception as e:
            logger.error(f"Failed to verify Neo4j connectivity: {e}")
            raise e

    def close(self):
        if self._driver is not None:
            logger.info("Closing Neo4j driver connection...")
            self._driver.close()
            self._driver = None

    @contextmanager
    def get_session(self, database: Optional[str] = None) -> Session:
        if self._driver is None:
            self.connect()
        db_name = database or settings.NEO4J_DATABASE
        session = self._driver.session(database=db_name)
        try:
            yield session
        finally:
            session.close()

    def execute_query(self, query: str, parameters: Optional[Dict[str, Any]] = None, database: Optional[str] = None) -> List[Dict[str, Any]]:
        with self.get_session(database=database) as session:
            result = session.run(query, parameters or {})
            return [record.data() for record in result]

    def execute_write(self, query: str, parameters: Optional[Dict[str, Any]] = None, database: Optional[str] = None) -> List[Dict[str, Any]]:
        with self.get_session(database=database) as session:
            def _tx_fn(tx):
                res = tx.run(query, parameters or {})
                return [record.data() for record in res]
            return session.execute_write(_tx_fn)

    def execute_single(self, query: str, parameters: Optional[Dict[str, Any]] = None, database: Optional[str] = None) -> Optional[Dict[str, Any]]:
        records = self.execute_query(query, parameters, database)
        return records[0] if records else None

    def initialize_schema(self) -> List[str]:
        """Creates unique constraints and search indexes idempotently."""
        statements = [
            "CREATE CONSTRAINT user_id IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE",
            "CREATE CONSTRAINT user_email IF NOT EXISTS FOR (u:User) REQUIRE u.email IS UNIQUE",
            "CREATE CONSTRAINT restaurant_id IF NOT EXISTS FOR (r:Restaurant) REQUIRE r.id IS UNIQUE",
            "CREATE CONSTRAINT dish_id IF NOT EXISTS FOR (d:Dish) REQUIRE d.id IS UNIQUE",
            "CREATE CONSTRAINT ingredient_id IF NOT EXISTS FOR (i:Ingredient) REQUIRE i.id IS UNIQUE",
            "CREATE CONSTRAINT allergen_id IF NOT EXISTS FOR (a:Allergen) REQUIRE a.id IS UNIQUE",
            "CREATE CONSTRAINT allergen_name IF NOT EXISTS FOR (a:Allergen) REQUIRE a.name IS UNIQUE",
            "CREATE CONSTRAINT activitylog_id IF NOT EXISTS FOR (al:ActivityLog) REQUIRE al.id IS UNIQUE",
            "CREATE INDEX restaurant_name_index IF NOT EXISTS FOR (r:Restaurant) ON (r.name)",
            "CREATE INDEX dish_name_index IF NOT EXISTS FOR (d:Dish) ON (d.name)",
            "CREATE INDEX ingredient_name_index IF NOT EXISTS FOR (i:Ingredient) ON (i.name)",
            "CREATE INDEX activitylog_timestamp_index IF NOT EXISTS FOR (al:ActivityLog) ON (al.timestamp)"
        ]
        applied = []
        with self.get_session() as session:
            for stmt in statements:
                try:
                    session.run(stmt)
                    applied.append(stmt)
                    logger.info(f"Schema statement executed: {stmt}")
                except Exception as e:
                    logger.warning(f"Error executing schema statement '{stmt}': {e}")
        return applied

db = Database()

def get_db() -> Database:
    return db
