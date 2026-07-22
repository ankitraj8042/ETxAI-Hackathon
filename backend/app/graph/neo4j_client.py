"""
DCBrain Knowledge Graph — Neo4j and In-Memory Hybrid Client
Provides a unified interface for agents to query the Knowledge Graph.
If Neo4j is unavailable, it automatically falls back to an in-memory graph simulation.
"""

import os
import json
from typing import Any, Dict, List, Optional
import asyncio

from app.core.config import settings
from app.core.dependencies import get_neo4j_driver
from app.graph.queries import GraphQueries


class GraphClient:
    """Unified Neo4j and In-Memory fallback client for relationship reasoning."""

    def __init__(self):
        self.queries = GraphQueries()
        self.use_neo4j = False
        self._nodes: Dict[str, Dict] = {}       # id -> node dict
        self._edges: List[Dict] = []            # list of edge dicts
        self._equipment_map: Dict[str, Dict] = {} # tag -> node dict
        self._ncr_map: Dict[str, Dict] = {}       # ncr_number -> node dict
        self._rfi_map: Dict[str, Dict] = {}       # rfi_number -> node dict
        self._test_map: Dict[str, Dict] = {}      # test_code -> node dict
        self._vendor_map: Dict[str, Dict] = {}    # code -> node dict
        self._task_map: Dict[str, Dict] = {}      # task_code -> node dict

    async def initialize(self):
        """Check Neo4j connectivity and initialize in-memory fallback if needed."""
        try:
            driver = await get_neo4j_driver()
            # Simple health check query
            async with driver.session() as session:
                await session.run("RETURN 1")
            self.use_neo4j = True
            print("🕸️ GraphClient: Connected to Neo4j database.")
        except Exception as e:
            self.use_neo4j = False
            print(f"⚠️ GraphClient: Neo4j not available ({e}). Falling back to In-Memory graph mode.")
            self._load_fallback_graph()

    def _load_fallback_graph(self):
        """Load graph from the local fallback JSON file."""
        filepath = "./backend/data/graph_store.json"
        
        # If the fallback JSON does not exist yet, trigger the seed generation
        if not os.path.exists(filepath):
            print("  Fallback graph file not found. Generating default seed data...")
            from app.graph.seed import write_local_graph_json
            write_local_graph_json()

        try:
            with open(filepath, "r") as f:
                data = json.load(f)
            
            self._nodes = {n["id"]: n for n in data.get("nodes", [])}
            self._edges = data.get("edges", [])

            # Index nodes by business keys for fast lookups
            for n in self._nodes.values():
                label = n.get("label")
                props = n.get("properties", {})
                
                if label == "Equipment":
                    self._equipment_map[props.get("tag")] = n
                elif label == "NCR":
                    self._ncr_map[props.get("ncr_number")] = n
                elif label == "RFI":
                    self._rfi_map[props.get("rfi_number")] = n
                elif label == "CommissioningTest":
                    self._test_map[props.get("test_code")] = n
                elif label == "Vendor":
                    self._vendor_map[props.get("code")] = n
                elif label == "ScheduleTask":
                    self._task_map[props.get("task_code")] = n

            print(f"🕸️ GraphClient: Loaded in-memory fallback graph ({len(self._nodes)} nodes, {len(self._edges)} edges)")
        except Exception as e:
            print(f"❌ GraphClient: Failed to load fallback graph: {e}")

    async def _run_query(self, query: str, params: dict = None) -> List[Dict]:
        """Execute a Cypher query on Neo4j."""
        driver = await get_neo4j_driver()
        async with driver.session() as session:
            result = await session.run(query, params or {})
            records = await result.data()
            return records

    # ── Unified API Methods ───────────────────────────────────────────

    async def get_equipment_context(self, tag: str) -> Dict:
        """Get full context for an equipment entity."""
        if not self.use_neo4j:
            await self._ensure_initialized()
            eq_node = self._equipment_map.get(tag)
            if not eq_node:
                return {}

            eq_id = eq_node["id"]
            zone = None
            vendor = None
            spec = None
            purchase_orders = []
            ncrs = []
            tests = []
            rfis = []
            tasks = []

            # Gather relationships
            for edge in self._edges:
                src, target, rel_type = edge["source"], edge["target"], edge["type"]
                
                if src == eq_id:
                    if rel_type == "INSTALLED_IN":
                        zone = self._nodes.get(target, {}).get("properties")
                    elif rel_type == "SUPPLIED_BY":
                        vendor = self._nodes.get(target, {}).get("properties")
                    elif rel_type == "SPECIFIED_IN":
                        spec = self._nodes.get(target, {}).get("properties")
                    elif rel_type == "ORDERED_VIA":
                        purchase_orders.append(self._nodes.get(target, {}).get("properties"))
                    elif rel_type == "TESTED_BY":
                        tests.append(self._nodes.get(target, {}).get("properties"))
                
                if target == eq_id:
                    if rel_type == "RAISED_AGAINST":
                        ncrs.append(self._nodes.get(src, {}).get("properties"))
                    elif rel_type == "REFERENCES": # PO references equipment
                        purchase_orders.append(self._nodes.get(src, {}).get("properties"))
                    elif rel_type == "RELATES_TO": # RFI relates to equipment
                        rfis.append(self._nodes.get(src, {}).get("properties"))
                    elif rel_type == "REQUIRES": # Task requires equipment
                        tasks.append(self._nodes.get(src, {}).get("properties"))

            # Remove duplicate POs or items if any
            po_list = list({x["id"]: x for x in purchase_orders if x}.values())

            return {
                "e": eq_node["properties"],
                "z": zone,
                "v": vendor,
                "s": spec,
                "purchase_orders": po_list,
                "ncrs": [n for n in ncrs if n],
                "tests": [t for t in tests if t],
                "rfis": [r for r in rfis if r],
                "tasks": [t for t in tasks if t]
            }

        # Neo4j path
        results = await self._run_query(
            self.queries.EQUIPMENT_FULL_CONTEXT,
            {"tag": tag}
        )
        return results[0] if results else {}

    async def get_equipment_impact_chain(self, tag: str) -> Dict:
        """Get the downstream impact of an equipment issue."""
        if not self.use_neo4j:
            await self._ensure_initialized()
            eq_node = self._equipment_map.get(tag)
            if not eq_node:
                return {}

            eq_id = eq_node["id"]
            direct_tasks = []
            direct_tests = []

            # Direct connections
            for edge in self._edges:
                src, target, rel_type = edge["source"], edge["target"], edge["type"]
                if target == eq_id and rel_type == "REQUIRES":
                    direct_tasks.append(self._nodes[src]["properties"]["task_code"])
                elif src == eq_id and rel_type == "TESTED_BY":
                    direct_tests.append(self._nodes[target]["properties"]["test_code"])

            # Downstream tasks (simple traversal)
            downstream_tasks = []
            visited_tasks = set(direct_tasks)
            queue = list(direct_tasks)
            
            while queue:
                current_code = queue.pop(0)
                current_node = self._task_map.get(current_code)
                if not current_node:
                    continue
                current_id = current_node["id"]
                
                # Find successor tasks
                for edge in self._edges:
                    if edge["target"] == current_id and edge["type"] == "DEPENDS_ON":
                        succ_node = self._nodes.get(edge["source"])
                        if succ_node and succ_node["label"] == "ScheduleTask":
                            succ_code = succ_node["properties"]["task_code"]
                            if succ_code not in visited_tasks:
                                visited_tasks.add(succ_code)
                                downstream_tasks.append(succ_code)
                                queue.append(succ_code)

            # Downstream tests
            downstream_tests = []
            visited_tests = set(direct_tests)
            queue_tests = list(direct_tests)

            while queue_tests:
                current_code = queue_tests.pop(0)
                current_node = self._test_map.get(current_code)
                if not current_node:
                    continue
                current_id = current_node["id"]
                
                # Find downstream tests
                for edge in self._edges:
                    if edge["target"] == current_id and edge["type"] == "DEPENDS_ON":
                        succ_node = self._nodes.get(edge["source"])
                        if succ_node and succ_node["label"] == "CommissioningTest":
                            succ_code = succ_node["properties"]["test_code"]
                            if succ_code not in visited_tests:
                                visited_tests.add(succ_code)
                                downstream_tests.append(succ_code)
                                queue_tests.append(succ_code)

            return {
                "equipment": tag,
                "direct_tasks": direct_tasks,
                "downstream_tasks": downstream_tasks,
                "direct_tests": direct_tests,
                "downstream_tests": downstream_tests
            }

        # Neo4j path
        results = await self._run_query(
            self.queries.EQUIPMENT_IMPACT_CHAIN,
            {"tag": tag}
        )
        return results[0] if results else {}

    async def get_ncr_impact(self, ncr_number: str) -> Dict:
        """Get the full impact chain of an NCR."""
        if not self.use_neo4j:
            await self._ensure_initialized()
            ncr_node = self._ncr_map.get(ncr_number)
            if not ncr_node:
                return {}

            props = ncr_node["properties"]
            eq_id = props.get("equipment_id")
            eq_node = self._nodes.get(eq_id)
            eq_tag = eq_node["properties"]["tag"] if eq_node else None
            
            # Use get_equipment_impact_chain to traverse the downstream graph
            impact = await self.get_equipment_impact_chain(eq_tag) if eq_tag else {}
            
            # Map codes back to nodes
            affected_tasks = [self._task_map[code]["properties"] for code in impact.get("direct_tasks", []) if code in self._task_map]
            downstream_tasks = [self._task_map[code]["properties"] for code in impact.get("downstream_tasks", []) if code in self._task_map]
            affected_tests = [self._test_map[code]["properties"] for code in impact.get("direct_tests", []) if code in self._test_map]
            blocked_tests = [self._test_map[code]["properties"] for code in impact.get("downstream_tests", []) if code in self._test_map]

            zone = None
            vendor = None
            if eq_node:
                eq_props = eq_node["properties"]
                zone_id = eq_props.get("zone_id")
                vendor_id = eq_props.get("vendor_id")
                zone = self._nodes.get(zone_id, {}).get("properties")
                vendor = self._nodes.get(vendor_id, {}).get("properties")

            return {
                "ncr": props,
                "e": eq_node["properties"] if eq_node else {},
                "z": zone,
                "v": vendor,
                "affected_tasks": affected_tasks,
                "downstream_tasks": downstream_tasks,
                "affected_tests": affected_tests,
                "blocked_tests": blocked_tests
            }

        # Neo4j path
        results = await self._run_query(
            self.queries.NCR_FULL_IMPACT,
            {"ncr_number": ncr_number}
        )
        return results[0] if results else {}

    async def get_vendor_profile(self, vendor_code: str) -> Dict:
        """Get vendor with all their equipment and history."""
        if not self.use_neo4j:
            await self._ensure_initialized()
            vendor_node = self._vendor_map.get(vendor_code)
            if not vendor_node:
                return {}

            vendor_id = vendor_node["id"]
            equipment = []
            orders = []
            ncrs = []

            # Gather vendor elements
            for n in self._nodes.values():
                props = n["properties"]
                if n["label"] == "Equipment" and props.get("vendor_id") == vendor_id:
                    equipment.append({
                        "tag": props.get("tag"),
                        "category": props.get("category"),
                        "status": props.get("status")
                    })
                elif n["label"] == "PurchaseOrder" and props.get("vendor_id") == vendor_id:
                    orders.append({
                        "po": props.get("po_number"),
                        "status": props.get("status")
                    })
                elif n["label"] == "NCR":
                    eq_node = self._nodes.get(props.get("equipment_id"))
                    if eq_node and eq_node["properties"].get("vendor_id") == vendor_id:
                        ncrs.append({
                            "ncr": props.get("ncr_number"),
                            "severity": props.get("severity")
                        })

            return {
                "v": vendor_node["properties"],
                "equipment": equipment,
                "orders": orders,
                "ncrs": ncrs
            }

        # Neo4j path
        results = await self._run_query(
            self.queries.VENDOR_EQUIPMENT_AND_HISTORY,
            {"vendor_code": vendor_code}
        )
        return results[0] if results else {}

    async def find_similar_rfis(self, rfi_number: str) -> List[Dict]:
        """Find previously resolved RFIs similar to the given one."""
        if not self.use_neo4j:
            await self._ensure_initialized()
            target_rfi = self._rfi_map.get(rfi_number)
            if not target_rfi:
                return []
            
            target_props = target_rfi["properties"]
            target_cat = target_props.get("category")
            
            similar = []
            for rfi in self._rfi_map.values():
                props = rfi["properties"]
                if props.get("rfi_number") != rfi_number and props.get("category") == target_cat and props.get("status") == "closed":
                    similar.append({
                        "rfi_number": props.get("rfi_number"),
                        "subject": props.get("subject"),
                        "answer": props.get("answer"),
                        "answered_date": props.get("answered_date")
                    })
            return similar[:5]

        # Neo4j path
        return await self._run_query(
            self.queries.SIMILAR_RFIS,
            {"rfi_number": rfi_number}
        )

    async def get_critical_path(self) -> List[Dict]:
        """Get all tasks on the critical path with their dependencies."""
        if not self.use_neo4j:
            await self._ensure_initialized()
            critical_tasks = []
            
            for task in self._task_map.values():
                props = task["properties"]
                if props.get("is_critical_path"):
                    task_id = task["id"]
                    
                    # Find predecessor task codes
                    predecessors = []
                    for edge in self._edges:
                        if edge["source"] == task_id and edge["type"] == "DEPENDS_ON":
                            pred_node = self._nodes.get(edge["target"])
                            if pred_node:
                                predecessors.append(pred_node["properties"]["task_code"])
                                
                    # Find equipment
                    equipment = []
                    for edge in self._edges:
                        if edge["source"] == task_id and edge["type"] == "REQUIRES":
                            eq_node = self._nodes.get(edge["target"])
                            if eq_node:
                                equipment.append(eq_node["properties"]["tag"])
                                
                    critical_tasks.append({
                        "task_code": props.get("task_code"),
                        "name": props.get("name"),
                        "start": props.get("planned_start"),
                        "end": props.get("planned_end"),
                        "status": props.get("status"),
                        "risk": props.get("risk_score"),
                        "equipment": equipment,
                        "predecessors": predecessors
                    })
            return sorted(critical_tasks, key=lambda x: x["start"])

        # Neo4j path
        return await self._run_query(self.queries.CRITICAL_PATH_TASKS)

    async def get_test_dependencies(self, test_code: str) -> Dict:
        """Get the dependency chain for a commissioning test."""
        if not self.use_neo4j:
            await self._ensure_initialized()
            test_node = self._test_map.get(test_code)
            if not test_node:
                return {}

            test_id = test_node["id"]
            eq_props = {}
            prerequisites = []
            dependents = []
            blocking_ncrs = []

            # Gather test attributes
            for edge in self._edges:
                src, target, rel_type = edge["source"], edge["target"], edge["type"]
                
                if src == test_id:
                    if rel_type == "TESTS":
                        eq_props = self._nodes.get(target, {}).get("properties", {})
                    elif rel_type == "DEPENDS_ON": # CX depends on prerequisite CX
                        prereq_node = self._nodes.get(target)
                        if prereq_node:
                            prerequisites.append(prereq_node["properties"]["test_code"])
                    elif rel_type == "BLOCKED_BY":
                        ncr_node = self._nodes.get(target)
                        if ncr_node:
                            blocking_ncrs.append(ncr_node["properties"]["ncr_number"])
                
                if target == test_id:
                    if rel_type == "DEPENDS_ON": # Dependent CX depends on this CX
                        dep_node = self._nodes.get(src)
                        if dep_node:
                            dependents.append(dep_node["properties"]["test_code"])

            return {
                "cx": test_node["properties"],
                "e": eq_props,
                "prerequisites": prerequisites,
                "dependents": dependents,
                "blocking_ncrs": blocking_ncrs
            }

        # Neo4j path
        results = await self._run_query(
            self.queries.TEST_DEPENDENCY_CHAIN,
            {"test_code": test_code}
        )
        return results[0] if results else {}

    async def find_alternative_vendors(self, equipment_tag: str) -> List[Dict]:
        """Find alternative vendors for equipment replacement."""
        if not self.use_neo4j:
            await self._ensure_initialized()
            eq_node = self._equipment_map.get(equipment_tag)
            if not eq_node:
                return []
            
            category = eq_node["properties"].get("category")
            current_vendor_id = eq_node["properties"].get("vendor_id")
            
            alternatives = []
            for vendor in self._vendor_map.values():
                vendor_id = vendor["id"]
                if vendor_id == current_vendor_id:
                    continue
                
                # Count equipment this vendor supplies in this category
                supplied_count = 0
                for eq in self._equipment_map.values():
                    if eq["properties"].get("vendor_id") == vendor_id and eq["properties"].get("category") == category:
                        supplied_count += 1
                
                # If they have history of supplying this equipment category
                if vendor["properties"].get("category") == eq_node["properties"].get("category") or supplied_count > 0:
                    alternatives.append({
                        "vendor_name": vendor["properties"]["name"],
                        "vendor_code": vendor["properties"]["code"],
                        "reliability": vendor["properties"]["reliability_score"],
                        "on_time_rate": vendor["properties"]["on_time_delivery_rate"],
                        "equipment_supplied": supplied_count
                    })
            return sorted(alternatives, key=lambda x: x["reliability"], reverse=True)[:5]

        # Neo4j path
        return await self._run_query(
            self.queries.FIND_ALTERNATIVE_VENDORS,
            {"tag": equipment_tag}
        )

    async def get_subgraph(self, entity_tag: str) -> Dict:
        """Get the subgraph nodes and edges around an entity for D3 graph visualization."""
        await self._ensure_initialized()
        
        # In-memory implementation is fast and returns standard nodes & links format
        center_id = None
        for n_id, n in self._nodes.items():
            if n["properties"].get("tag") == entity_tag or n["properties"].get("task_code") == entity_tag or n["properties"].get("ncr_number") == entity_tag or n["properties"].get("test_code") == entity_tag:
                center_id = n_id
                break
        
        if not center_id:
            return {"nodes": [], "links": []}

        sub_node_ids = {center_id}
        sub_edges = []

        # Find 1st degree connections
        for edge in self._edges:
            src, target = edge["source"], edge["target"]
            if src == center_id or target == center_id:
                sub_node_ids.add(src)
                sub_node_ids.add(target)
                sub_edges.append(edge)

        # Find 2nd degree connections
        for edge in self._edges:
            src, target = edge["source"], edge["target"]
            if (src in sub_node_ids or target in sub_node_ids) and edge not in sub_edges:
                sub_node_ids.add(src)
                sub_node_ids.add(target)
                sub_edges.append(edge)

        nodes_list = []
        for n_id in sub_node_ids:
            node = self._nodes.get(n_id)
            if node:
                nodes_list.append({
                    "id": node["id"],
                    "label": node["label"],
                    "name": node["properties"].get("tag") or node["properties"].get("name") or node["properties"].get("subject") or node["properties"].get("ncr_number") or node["properties"].get("task_code") or node["properties"].get("title"),
                    "properties": node["properties"]
                })

        links_list = []
        for edge in sub_edges:
            links_list.append({
                "source": edge["source"],
                "target": edge["target"],
                "type": edge["type"]
            })

        return {"nodes": nodes_list, "links": links_list}

    async def _ensure_initialized(self):
        """Helper to ensure graph dataset is loaded in fallback mode."""
        if not self._nodes and not self.use_neo4j:
            await self.initialize()


# Singleton instance
graph_client = GraphClient()
