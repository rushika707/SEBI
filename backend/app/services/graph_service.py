import os
import json
import logging
from typing import List, Dict, Any, Optional
import networkx as nx
from app.core.config import settings

logger = logging.getLogger("sebi_copilot.graph_service")

class GraphService:
    def __init__(self):
        self.fallback_mode = False
        self.driver = None
        self.fallback_file = "sebi_graph.json"
        self.local_graph = nx.DiGraph()
        
        # Load local graph if exists
        self.load_local_graph()

        try:
            from neo4j import GraphDatabase
            logger.info(f"Attempting to connect to Neo4j at {settings.NEO4J_URI}")
            self.driver = GraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD) if settings.NEO4J_PASSWORD else None
            )
            # Verify connectivity
            self.driver.verify_connectivity()
            logger.info("Successfully connected to Neo4j.")
        except Exception as e:
            logger.warning(f"Neo4j connection failed: {e}. Switching to NetworkX graph fallback.")
            self.driver = None
            self.fallback_mode = True

    def load_local_graph(self):
        if os.path.exists(self.fallback_file):
            try:
                with open(self.fallback_file, "r") as f:
                    data = json.load(f)
                    for node in data.get("nodes", []):
                        self.local_graph.add_node(node["id"], **node.get("properties", {}), label=node.get("label"))
                    for edge in data.get("edges", []):
                        self.local_graph.add_edge(edge["source"], edge["target"], type=edge.get("type"))
                logger.info(f"Loaded {len(self.local_graph.nodes)} nodes and {len(self.local_graph.edges)} edges from {self.fallback_file}.")
            except Exception as e:
                logger.error(f"Error loading local graph file: {e}")

    def save_local_graph(self):
        try:
            nodes = [{"id": n, "label": self.local_graph.nodes[n].get("label"), "properties": {k: v for k, v in self.local_graph.nodes[n].items() if k != "label"}} for n in self.local_graph.nodes]
            edges = [{"source": u, "target": v, "type": self.local_graph.edges[u, v].get("type")} for u, v in self.local_graph.edges]
            with open(self.fallback_file, "w") as f:
                json.dump({"nodes": nodes, "edges": edges}, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving local graph file: {e}")

    def add_node(self, node_id: str, label: str, properties: Dict[str, Any]):
        if self.fallback_mode or not self.driver:
            self.local_graph.add_node(node_id, label=label, **properties)
            self.save_local_graph()
            return

        def _create_node(tx):
            # Dynamic labels in Cypher requires parameter formatting or apoc
            query = f"MERGE (n:{label} {{id: $id}}) SET n += $props RETURN n"
            tx.run(query, id=node_id, props=properties)

        try:
            with self.driver.session() as session:
                session.execute_write(_create_node)
        except Exception as e:
            logger.error(f"Neo4j write failed: {e}. Writing to NetworkX fallback.")
            self.local_graph.add_node(node_id, label=label, **properties)
            self.save_local_graph()

    def add_relationship(self, source_id: str, target_id: str, rel_type: str):
        if self.fallback_mode or not self.driver:
            self.local_graph.add_edge(source_id, target_id, type=rel_type)
            self.save_local_graph()
            return

        def _create_rel(tx):
            query = (
                "MATCH (a {id: $source_id}), (b {id: $target_id}) "
                f"MERGE (a)-[r:{rel_type}]->(b) "
                "RETURN r"
            )
            tx.run(query, source_id=source_id, target_id=target_id)

        try:
            with self.driver.session() as session:
                session.execute_write(_create_rel)
        except Exception as e:
            logger.error(f"Neo4j relationship failed: {e}. Writing to NetworkX fallback.")
            self.local_graph.add_edge(source_id, target_id, type=rel_type)
            self.save_local_graph()

    def get_entire_graph(self) -> Dict[str, Any]:
        if self.fallback_mode or not self.driver:
            nodes = []
            for n in self.local_graph.nodes:
                node_data = self.local_graph.nodes[n]
                nodes.append({
                    "id": n,
                    "label": node_data.get("label", "Node"),
                    "properties": {k: v for k, v in node_data.items() if k != "label"}
                })
            edges = []
            for u, v in self.local_graph.edges:
                edges.append({
                    "source": u,
                    "target": v,
                    "type": self.local_graph.edges[u, v].get("type", "CONNECTED")
                })
            return {"nodes": nodes, "edges": edges}

        query = (
            "MATCH (n) "
            "OPTIONAL MATCH (n)-[r]->(m) "
            "RETURN n, r, m"
        )
        try:
            with self.driver.session() as session:
                result = session.run(query)
                nodes_map = {}
                edges = []
                for record in result:
                    n = record["n"]
                    if n:
                        n_id = n["id"]
                        labels = list(n.labels)
                        nodes_map[n_id] = {
                            "id": n_id,
                            "label": labels[0] if labels else "Node",
                            "properties": dict(n)
                        }
                    m = record["m"]
                    r = record["r"]
                    if m and r:
                        m_id = m["id"]
                        edges.append({
                            "source": n_id,
                            "target": m_id,
                            "type": r.type
                        })
                return {"nodes": list(nodes_map.values()), "edges": edges}
        except Exception as e:
            logger.error(f"Neo4j read failed: {e}. Reading from NetworkX fallback.")
            self.fallback_mode = True
            return self.get_entire_graph()

    def get_downstream_impact(self, regulation_id: str) -> List[Dict[str, Any]]:
        # Traverse from Regulation -> Clause -> Obligation -> Department -> Employee/Evidence
        if self.fallback_mode or not self.driver:
            # Local BFS traversal
            impacted = []
            if not self.local_graph.has_node(regulation_id):
                return impacted
            
            # Simple BFS/DFS traversal matching specific nodes
            queue = [regulation_id]
            visited = {regulation_id}
            while queue:
                current = queue.pop(0)
                node_data = self.local_graph.nodes[current]
                if current != regulation_id:
                    impacted.append({
                        "id": current,
                        "label": node_data.get("label"),
                        "properties": {k: v for k, v in node_data.items() if k != "label"}
                    })
                for neighbor in self.local_graph.successors(current):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append(neighbor)
            return impacted

        query = (
            "MATCH (r:Regulation {id: $reg_id})-[*1..4]->(downstream) "
            "RETURN downstream, labels(downstream)[0] as label"
        )
        try:
            with self.driver.session() as session:
                result = session.run(query, reg_id=regulation_id)
                impacted = []
                for record in result:
                    node = record["downstream"]
                    label = record["label"]
                    impacted.append({
                        "id": node["id"],
                        "label": label,
                        "properties": dict(node)
                    })
                return impacted
        except Exception as e:
            logger.error(f"Neo4j path query failed: {e}")
            return []

    def close(self):
        if self.driver:
            self.driver.close()

# Global instance
graph_service = GraphService()
