from typing import Any, Dict, List, Optional, Set
from app.database import db

class GraphRepository:
    # Color palette constants
    COLOR_RESTAURANT = "#245C46"   # Forest green
    COLOR_DISH = "#DD6B20"         # Orange
    COLOR_INGREDIENT = "#3182CE"   # Blue
    COLOR_ALLERGEN = "#C74747"     # Red

    @classmethod
    def _format_node(cls, node_type: str, props: Dict[str, Any]) -> Dict[str, Any]:
        node_id = props.get("id") or str(props.get("name"))
        name = props.get("name", "Unknown")
        color_map = {
            "Restaurant": cls.COLOR_RESTAURANT,
            "Dish": cls.COLOR_DISH,
            "Ingredient": cls.COLOR_INGREDIENT,
            "Allergen": cls.COLOR_ALLERGEN
        }
        color = color_map.get(node_type, "#718096")
        
        return {
            "data": {
                "id": node_id,
                "label": name,
                "type": node_type,
                "color": color,
                "properties": props
            }
        }

    @classmethod
    def _format_edge(cls, rel_type: str, source_id: str, target_id: str, props: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        edge_id = f"{source_id}->{rel_type}->{target_id}"
        return {
            "data": {
                "id": edge_id,
                "source": source_id,
                "target": target_id,
                "label": rel_type,
                "properties": props or {}
            }
        }

    def get_graph_data(
        self,
        limit: int = 100,
        node_types: Optional[List[str]] = None,
        search: Optional[str] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        nodes_dict: Dict[str, Dict[str, Any]] = {}
        edges_dict: Dict[str, Dict[str, Any]] = {}

        types = [t.strip().capitalize() for t in node_types] if node_types else ["Restaurant", "Dish", "Ingredient", "Allergen"]

        # Fetch nodes with limit
        type_filter = " OR ".join([f"'{t}' IN labels(n)" for t in types])
        where_clauses = [f"({type_filter})"]
        params: Dict[str, Any] = {"limit": limit}

        if search:
            where_clauses.append("toLower(n.name) CONTAINS toLower($search)")
            params["search"] = search.strip()

        query_nodes = f"""
        MATCH (n)
        WHERE {' AND '.join(where_clauses)}
        RETURN n, [l IN labels(n) WHERE l IN ['Restaurant', 'Dish', 'Ingredient', 'Allergen']][0] as node_type
        LIMIT $limit
        """
        node_records = db.execute_query(query_nodes, params)
        for rec in node_records:
            n = rec["n"]
            nt = rec["node_type"] or "Unknown"
            if n.get("id"):
                nodes_dict[n["id"]] = self._format_node(nt, dict(n))

        if not nodes_dict:
            return {"nodes": [], "edges": []}

        # Fetch edges connecting the loaded nodes
        node_ids = list(nodes_dict.keys())
        query_edges = """
        MATCH (a)-[r:OFFERS|CONTAINS|CONTAINS_ALLERGEN|MAY_CONTAIN]->(b)
        WHERE a.id IN $node_ids AND b.id IN $node_ids
        RETURN a.id as source, b.id as target, type(r) as rel_type, properties(r) as props
        LIMIT 200
        """
        edge_records = db.execute_query(query_edges, {"node_ids": node_ids})
        for rec in edge_records:
            edge = self._format_edge(rec["rel_type"], rec["source"], rec["target"], rec["props"])
            edges_dict[edge["data"]["id"]] = edge

        return {
            "nodes": list(nodes_dict.values()),
            "edges": list(edges_dict.values())
        }

    def expand_node(self, node_id: str, limit: int = 30) -> Dict[str, List[Dict[str, Any]]]:
        nodes_dict: Dict[str, Dict[str, Any]] = {}
        edges_dict: Dict[str, Dict[str, Any]] = {}

        query = """
        MATCH (center {id: $node_id})
        MATCH (center)-[r:OFFERS|CONTAINS|CONTAINS_ALLERGEN|MAY_CONTAIN]-(neighbor)
        RETURN 
            center, 
            [l IN labels(center) WHERE l IN ['Restaurant', 'Dish', 'Ingredient', 'Allergen']][0] as center_type,
            r, 
            type(r) as rel_type, 
            startNode(r).id as source_id, 
            endNode(r).id as target_id,
            neighbor, 
            [l IN labels(neighbor) WHERE l IN ['Restaurant', 'Dish', 'Ingredient', 'Allergen']][0] as neighbor_type
        LIMIT $limit
        """
        records = db.execute_query(query, {"node_id": node_id, "limit": limit})
        for rec in records:
            c = rec["center"]
            ct = rec["center_type"] or "Unknown"
            if c.get("id") and c["id"] not in nodes_dict:
                nodes_dict[c["id"]] = self._format_node(ct, dict(c))

            nbr = rec["neighbor"]
            nt = rec["neighbor_type"] or "Unknown"
            if nbr.get("id") and nbr["id"] not in nodes_dict:
                nodes_dict[nbr["id"]] = self._format_node(nt, dict(nbr))

            edge = self._format_edge(rec["rel_type"], rec["source_id"], rec["target_id"], rec["r"])
            edges_dict[edge["data"]["id"]] = edge

        return {
            "nodes": list(nodes_dict.values()),
            "edges": list(edges_dict.values())
        }

    def get_allergen_paths(self, restaurant_id: Optional[str] = None, allergen_id: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        nodes_dict: Dict[str, Dict[str, Any]] = {}
        edges_dict: Dict[str, Dict[str, Any]] = {}

        where_parts = []
        params: Dict[str, Any] = {}
        if restaurant_id:
            where_parts.append("r.id = $r_id")
            params["r_id"] = restaurant_id
        if allergen_id:
            where_parts.append("a.id = $a_id")
            params["a_id"] = allergen_id

        where_clause = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""

        # Path 1: Restaurant -> Dish -> Ingredient -> Allergen
        query_direct = f"""
        MATCH path = (r:Restaurant)-[:OFFERS]->(d:Dish)-[:CONTAINS]->(i:Ingredient)-[:CONTAINS_ALLERGEN]->(a:Allergen)
        {where_clause}
        RETURN r, d, i, a
        LIMIT 50
        """
        records1 = db.execute_query(query_direct, params)
        for rec in records1:
            for item, label in [(rec["r"], "Restaurant"), (rec["d"], "Dish"), (rec["i"], "Ingredient"), (rec["a"], "Allergen")]:
                if item.get("id") and item["id"] not in nodes_dict:
                    nodes_dict[item["id"]] = self._format_node(label, dict(item))
            
            e1 = self._format_edge("OFFERS", rec["r"]["id"], rec["d"]["id"])
            e2 = self._format_edge("CONTAINS", rec["d"]["id"], rec["i"]["id"])
            e3 = self._format_edge("CONTAINS_ALLERGEN", rec["i"]["id"], rec["a"]["id"])
            for e in [e1, e2, e3]:
                edges_dict[e["data"]["id"]] = e

        # Path 2: Restaurant -> Dish -> MAY_CONTAIN -> Allergen
        query_may = f"""
        MATCH path = (r:Restaurant)-[:OFFERS]->(d:Dish)-[:MAY_CONTAIN]->(a:Allergen)
        {where_clause}
        RETURN r, d, a
        LIMIT 50
        """
        records2 = db.execute_query(query_may, params)
        for rec in records2:
            for item, label in [(rec["r"], "Restaurant"), (rec["d"], "Dish"), (rec["a"], "Allergen")]:
                if item.get("id") and item["id"] not in nodes_dict:
                    nodes_dict[item["id"]] = self._format_node(label, dict(item))
            
            e1 = self._format_edge("OFFERS", rec["r"]["id"], rec["d"]["id"])
            e2 = self._format_edge("MAY_CONTAIN", rec["d"]["id"], rec["a"]["id"])
            for e in [e1, e2]:
                edges_dict[e["data"]["id"]] = e

        return {
            "nodes": list(nodes_dict.values()),
            "edges": list(edges_dict.values())
        }

graph_repo = GraphRepository()
