"""The neo4j handler for writing the knowledge graph to neo4j."""

import logging
from typing import Mapping, Sequence

from neo4j import GraphDatabase, ManagedTransaction

from prometheus.graph.graph_types import (
    KnowledgeGraphNode,
    Neo4jASTNode,
    Neo4jFileNode,
    Neo4jHasASTEdge,
    Neo4jHasFileEdge,
    Neo4jHasTextEdge,
    Neo4jNextChunkEdge,
    Neo4jTextNode,
)
from prometheus.graph.knowledge_graph import KnowledgeGraph


class KnowledgeGraphHandler:
    """The handler to writing the Knowledge graph to neo4j."""

    def __init__(self, driver: GraphDatabase.driver, batch_size: int):
        """
        Args:
          driver: The neo4j driver.
          batch_size: The maximum number of nodes/edges written to neo4j each time.
        """
        self.driver = driver
        self.batch_size = batch_size
        # initialize the database and logger
        self._init_database()
        self._logger = logging.getLogger("prometheus.neo4j.knowledge_graph_handler")

    def _init_database(self):
        """Initialization of the neo4j database."""

        # Create constraints for node_id attributes.
        # It also means that node_id will be indexed.
        queries = [
            "CREATE CONSTRAINT unique_file_node_id IF NOT EXISTS "
            "FOR (n:FileNode) REQUIRE n.node_id IS UNIQUE",
            "CREATE CONSTRAINT unique_ast_node_id IF NOT EXISTS "
            "FOR (n:ASTNode) REQUIRE n.node_id IS UNIQUE",
            "CREATE CONSTRAINT unique_text_node_id IF NOT EXISTS "
            "FOR (n:TextNode) REQUIRE n.node_id IS UNIQUE",
        ]
        with self.driver.session() as session:
            for query in queries:
                session.run(query)

    def _write_file_nodes(self, tx: ManagedTransaction, file_nodes: Sequence[Neo4jFileNode]):
        """Write Neo4jFileNode to neo4j."""
        self._logger.debug(f"Writing {len(file_nodes)} FileNode to neo4j")
        query = """
      UNWIND $file_nodes AS file_node
      MERGE (a:FileNode {node_id: file_node.node_id})
      SET a.basename = file_node.basename,
          a.relative_path = file_node.relative_path
    """
        for i in range(0, len(file_nodes), self.batch_size):
            file_nodes_batch = file_nodes[i : i + self.batch_size]
            tx.run(query, file_nodes=file_nodes_batch)

    def _write_ast_nodes(self, tx: ManagedTransaction, ast_nodes: Sequence[Neo4jASTNode]):
        """Write Neo4jASTNode to neo4j."""
        self._logger.debug(f"Writing {len(ast_nodes)} ASTNode to neo4j")
        query = """
      UNWIND $ast_nodes AS ast_node
      MERGE (a:ASTNode {node_id: ast_node.node_id})
      SET a.start_line = ast_node.start_line,
          a.end_line = ast_node.end_line,
          a.type = ast_node.type,
          a.text = ast_node.text
    """
        for i in range(0, len(ast_nodes), self.batch_size):
            ast_nodes_batch = ast_nodes[i : i + self.batch_size]
            tx.run(query, ast_nodes=ast_nodes_batch)

    def _write_text_nodes(self, tx: ManagedTransaction, text_nodes: Sequence[Neo4jTextNode]):
        """Write Neo4jTextNode to neo4j."""
        self._logger.debug(f"Writing {len(text_nodes)} TextNode to neo4j")
        query = """
      UNWIND $text_nodes AS text_node
      MERGE (a:TextNode {node_id: text_node.node_id})
      SET a.text = text_node.text,
          a.metadata = text_node.metadata
    """
        for i in range(0, len(text_nodes), self.batch_size):
            text_nodes_batch = text_nodes[i : i + self.batch_size]
            tx.run(query, text_nodes=text_nodes_batch)

    def _write_has_file_edges(
        self, tx: ManagedTransaction, has_file_edges: Sequence[Neo4jHasFileEdge]
    ):
        """Write Neo4jHasFileEdge to neo4j."""
        self._logger.debug(f"Writing {len(has_file_edges)} HasFileEdge to neo4j")
        query = """
      UNWIND $edges AS edge
      MATCH (source:FileNode), (target:FileNode)
      WHERE source.node_id = edge.source.node_id AND target.node_id = edge.target.node_id
      MERGE (source)-[:HAS_FILE]->(target)
    """
        for i in range(0, len(has_file_edges), self.batch_size):
            has_file_edges_batch = has_file_edges[i : i + self.batch_size]
            tx.run(query, edges=has_file_edges_batch)

    def _write_has_ast_edges(
        self, tx: ManagedTransaction, has_ast_edges: Sequence[Neo4jHasASTEdge]
    ):
        """Write Neo4jHasASTEdge to neo4j."""
        self._logger.debug(f"Writing {len(has_ast_edges)} HasASTEdge to neo4j")
        query = """
      UNWIND $edges AS edge
      MATCH (source:FileNode), (target:ASTNode)
      WHERE source.node_id = edge.source.node_id AND target.node_id = edge.target.node_id
      MERGE (source)-[:HAS_AST]->(target)
    """
        for i in range(0, len(has_ast_edges), self.batch_size):
            has_ast_edges_batch = has_ast_edges[i : i + self.batch_size]
            tx.run(query, edges=has_ast_edges_batch)

    def _write_has_text_edges(
        self, tx: ManagedTransaction, has_text_edges: Sequence[Neo4jHasTextEdge]
    ):
        """Write Neo4jHasTextEdge to neo4j."""
        self._logger.debug(f"Writing {len(has_text_edges)} HasTextEdges to neo4j")
        query = """
      UNWIND $edges AS edge
      MATCH (source:FileNode), (target:TextNode)
      WHERE source.node_id = edge.source.node_id AND target.node_id = edge.target.node_id
      MERGE (source)-[:HAS_TEXT]->(target)
    """
        for i in range(0, len(has_text_edges), self.batch_size):
            has_text_edges_batch = has_text_edges[i : i + self.batch_size]
            tx.run(query, edges=has_text_edges_batch)

    def write_parent_of_edges(self, parent_of_edges):
        self._logger.debug(f"Writing {len(parent_of_edges)} ParentOfEdge to neo4j")

        query = """
            UNWIND $edges AS edge
            MATCH (source:ASTNode {node_id: edge.source.node_id})
            MATCH (target:ASTNode {node_id: edge.target.node_id})
            MERGE (source)-[:PARENT_OF]->(target)
        """

        for i in range(0, len(parent_of_edges), self.batch_size):
            parent_of_edges_batch = parent_of_edges[i : i + self.batch_size]
            edge_dicts = [
                {
                    "source": {"node_id": e.source.node_id},
                    "target": {"node_id": e.target.node_id},
                }
                for e in parent_of_edges_batch
            ]
            with self.driver.session() as session:
                session.write_transaction(lambda tx: tx.run(query, edges=edge_dicts))

    def _write_next_chunk_edges(
        self, tx: ManagedTransaction, next_chunk_edges: Sequence[Neo4jNextChunkEdge]
    ):
        """Write Neo4jNextChunkEdge to neo4j."""
        self._logger.debug(f"Writing {len(next_chunk_edges)} NextChunkEdge to neo4j")
        query = """
      UNWIND $edges AS edge
      MATCH (source:TextNode), (target:TextNode)
      WHERE source.node_id = edge.source.node_id AND target.node_id = edge.target.node_id
      MERGE (source)-[:NEXT_CHUNK]->(target)
    """
        for i in range(0, len(next_chunk_edges), self.batch_size):
            next_chunk_edges_batch = next_chunk_edges[i : i + self.batch_size]
            tx.run(query, edges=next_chunk_edges_batch)

    def write_knowledge_graph(self, kg: KnowledgeGraph):
        """Write the knowledge graph to neo4j.

        Args:
          kg: The knowledge graph to write to neo4j.
        """
        self._logger.info("Writing knowledge graph to neo4j")
        with self.driver.session() as session:
            session.execute_write(self._write_file_nodes, kg.get_neo4j_file_nodes())
            session.execute_write(self._write_ast_nodes, kg.get_neo4j_ast_nodes())
            session.execute_write(self._write_text_nodes, kg.get_neo4j_text_nodes())

            session.execute_write(self._write_has_ast_edges, kg.get_neo4j_has_ast_edges())
            session.execute_write(self._write_has_file_edges, kg.get_neo4j_has_file_edges())
            session.execute_write(self._write_has_text_edges, kg.get_neo4j_has_text_edges())
            session.execute_write(self._write_next_chunk_edges, kg.get_neo4j_next_chunk_edges())
        self.write_parent_of_edges(kg.get_parent_of_edges())

    def _read_file_nodes(
        self, tx: ManagedTransaction, root_node_id: int
    ) -> Sequence[KnowledgeGraphNode]:
        """
        Read all FileNode nodes that are reachable from the specified root_node_id (including the root node itself).

        Args:
            tx (ManagedTransaction): An active Neo4j transaction.
            root_node_id (int): The node id of the root node.

        Returns:
            Sequence[KnowledgeGraphNode]: List of FileNode KnowledgeGraphNode objects.
        """
        query = """
        MATCH (root:FileNode {node_id: $root_node_id})
        RETURN root.node_id AS node_id, root.basename AS basename, root.relative_path AS relative_path
        UNION
        MATCH (root:FileNode {node_id: $root_node_id})-[:HAS_FILE*]->(n:FileNode)
        RETURN n.node_id AS node_id, n.basename AS basename, n.relative_path AS relative_path
        """
        result = tx.run(query, root_node_id=root_node_id)
        return [KnowledgeGraphNode.from_neo4j_file_node(record.data()) for record in result]

    def _read_ast_nodes(
        self, tx: ManagedTransaction, root_node_id: int
    ) -> Sequence[KnowledgeGraphNode]:
        """
        Read all ASTNode nodes related to the file tree rooted at root_node_id:
          - Traverse from the root FileNode via HAS_FILE* to get all reachable FileNodes.
          - For each FileNode, get its AST root node via HAS_AST, and all its AST descendants via PARENT_OF*.

        Args:
            tx (ManagedTransaction): An active Neo4j transaction.
            root_node_id (int): The node id of the root FileNode.

        Returns:
            Sequence[KnowledgeGraphNode]: List of ASTNode KnowledgeGraphNode objects.
        """
        query = """
        MATCH (root {node_id: $root_node_id})
        OPTIONAL MATCH (root)-[*]->(n:ASTNode)
        RETURN DISTINCT n.node_id AS node_id, n.start_line AS start_line, n.end_line AS end_line, n.type AS type, n.text AS text
        """
        result = tx.run(query, root_node_id=root_node_id)
        return [KnowledgeGraphNode.from_neo4j_ast_node(record.data()) for record in result]

    def _read_text_nodes(
        self, tx: ManagedTransaction, root_node_id: int
    ) -> Sequence[KnowledgeGraphNode]:
        """
        Read all TextNode nodes that are reachable from the specified root_node_id (regardless of edge type).

        Args:
            tx (ManagedTransaction): An active Neo4j transaction.
            root_node_id (int): The node id of the root node.

        Returns:
            Sequence[KnowledgeGraphNode]: List of TextNode KnowledgeGraphNode objects.
        """
        query = """
        MATCH (root {node_id: $root_node_id})
        OPTIONAL MATCH (root)-[*]->(n:TextNode)
        RETURN DISTINCT n.node_id AS node_id, n.text AS text, n.metadata AS metadata
        """
        result = tx.run(query, root_node_id=root_node_id)
        return [KnowledgeGraphNode.from_neo4j_text_node(record.data()) for record in result]

    def _read_parent_of_edges(
        self, tx: ManagedTransaction, root_node_id: int
    ) -> Sequence[Mapping[str, int]]:
        """
        Read all PARENT_OF edges where both source and target ASTNode are reachable from the subtree rooted at root_node_id.

        Args:
            tx (ManagedTransaction): An active Neo4j transaction.
            root_node_id (int): The node id of the root FileNode.

        Returns:
            Sequence[Mapping[str, int]]: List of dicts with source_id and target_id for each PARENT_OF edge.
        """
        query = """
        // Find all reachable ASTNodes (from the file tree)
        MATCH (root:FileNode {node_id: $root_node_id})
        OPTIONAL MATCH (root)-[*]->(ast:ASTNode)
        WITH collect(ast) AS all_ast_nodes
        UNWIND all_ast_nodes AS node1
        WITH node1, all_ast_nodes WHERE node1 IS NOT NULL
        // Find PARENT_OF edges only between those ASTNodes
        MATCH (node1)-[:PARENT_OF]->(node2:ASTNode)
        WHERE node2 IN all_ast_nodes
        RETURN node1.node_id AS source_id, node2.node_id AS target_id
        """
        result = tx.run(query, root_node_id=root_node_id)
        return [record.data() for record in result]

    def _read_has_file_edges(
        self, tx: ManagedTransaction, root_node_id: int
    ) -> Sequence[Mapping[str, int]]:
        """
        Read all HAS_FILE edges that are reachable from the specified root_node_id (i.e., only those
        between FileNodes in the subtree of root_node_id, including root itself).

        Args:
            tx (ManagedTransaction): An active Neo4j transaction.
            root_node_id (int): The node id of the root FileNode.

        Returns:
            Sequence[Mapping[str, int]]: List of dicts with source_id and target_id for each HAS_FILE edge.
        """
        query = """
            MATCH p = (root:FileNode {node_id: $root_node_id})-[:HAS_FILE*0..]->(n:FileNode)
            WITH collect(DISTINCT n) AS nodes_in_subtree
            UNWIND nodes_in_subtree AS src
            MATCH (src)-[:HAS_FILE]->(dst:FileNode)
            WHERE dst IN nodes_in_subtree
            RETURN DISTINCT src.node_id AS source_id, dst.node_id AS target_id
            """
        result = tx.run(query, root_node_id=root_node_id)
        return [record.data() for record in result]

    def _read_has_ast_edges(
        self, tx: ManagedTransaction, root_node_id: int
    ) -> Sequence[Mapping[str, int]]:
        """
        Read all HAS_AST edges where the source FileNode is in the subtree rooted at root_node_id.

        Args:
            tx (ManagedTransaction): An active Neo4j transaction.
            root_node_id (int): The node id of the root FileNode.

        Returns:
            Sequence[Mapping[str, int]]: List of dicts with source_id and target_id for each HAS_AST edge.
        """
        query = """
        // Find all reachable FileNodes (including root)
        MATCH (root:FileNode {node_id: $root_node_id})
        OPTIONAL MATCH (root)-[:HAS_FILE*]->(subfile:FileNode)
        WITH collect(root) + collect(subfile) AS all_file_nodes
        UNWIND all_file_nodes AS file_node
        WITH file_node WHERE file_node IS NOT NULL
        // Find HAS_AST edges from these FileNodes
        MATCH (file_node)-[:HAS_AST]->(ast:ASTNode)
        RETURN file_node.node_id AS source_id, ast.node_id AS target_id
        """
        result = tx.run(query, root_node_id=root_node_id)
        return [record.data() for record in result]

    def _read_has_text_edges(
        self, tx: ManagedTransaction, root_node_id: int
    ) -> Sequence[Mapping[str, int]]:
        """
        Read all HAS_TEXT edges where the source FileNode is in the subtree rooted at root_node_id.

        Args:
            tx (ManagedTransaction): An active Neo4j transaction.
            root_node_id (int): The node id of the root FileNode.

        Returns:
            Sequence[Mapping[str, int]]: List of dicts with source_id and target_id for each HAS_TEXT edge.
        """
        query = """
        // Find all reachable FileNodes (including root)
        MATCH (root:FileNode {node_id: $root_node_id})
        OPTIONAL MATCH (root)-[:HAS_FILE*]->(subfile:FileNode)
        WITH collect(root) + collect(subfile) AS all_file_nodes
        UNWIND all_file_nodes AS file_node
        WITH file_node WHERE file_node IS NOT NULL
        // Find HAS_TEXT edges from these FileNodes
        MATCH (file_node)-[:HAS_TEXT]->(text:TextNode)
        RETURN file_node.node_id AS source_id, text.node_id AS target_id
        """
        result = tx.run(query, root_node_id=root_node_id)
        return [record.data() for record in result]

    def _read_next_chunk_edges(
        self, tx: ManagedTransaction, root_node_id: int
    ) -> Sequence[Mapping[str, int]]:
        """
        Read all NEXT_CHUNK edges between TextNodes that are reachable from the subtree rooted at root_node_id.

        Args:
            tx (ManagedTransaction): An active Neo4j transaction.
            root_node_id (int): The node id of the root FileNode.

        Returns:
            Sequence[Mapping[str, int]]: List of dicts with source_id and target_id for each NEXT_CHUNK edge.
        """
        query = """
        // Find all reachable TextNodes (from the file tree)
        MATCH (root:FileNode {node_id: $root_node_id})
        OPTIONAL MATCH (root)-[*]->(text_node:TextNode)
        WITH collect(text_node) AS all_text_nodes
        UNWIND all_text_nodes AS node1
        WITH node1, all_text_nodes WHERE node1 IS NOT NULL
        // Find NEXT_CHUNK edges only between those TextNodes
        MATCH (node1)-[:NEXT_CHUNK]->(node2:TextNode)
        WHERE node2 IN all_text_nodes
        RETURN node1.node_id AS source_id, node2.node_id AS target_id
        """
        result = tx.run(query, root_node_id=root_node_id)
        return [record.data() for record in result]

    def read_knowledge_graph(
        self,
        root_node_id: int,
        max_ast_depth: int,
        chunk_size: int,
        chunk_overlap: int,
    ) -> KnowledgeGraph:
        """Read KnowledgeGraph from neo4j."""
        self._logger.info("Reading knowledge graph from neo4j")
        with self.driver.session() as session:
            return KnowledgeGraph.from_neo4j(
                root_node_id,
                max_ast_depth,
                chunk_size,
                chunk_overlap,
                session.execute_read(self._read_file_nodes, root_node_id=root_node_id),
                session.execute_read(self._read_ast_nodes, root_node_id=root_node_id),
                session.execute_read(self._read_text_nodes, root_node_id=root_node_id),
                session.execute_read(self._read_parent_of_edges, root_node_id=root_node_id),
                session.execute_read(self._read_has_file_edges, root_node_id=root_node_id),
                session.execute_read(self._read_has_ast_edges, root_node_id=root_node_id),
                session.execute_read(self._read_has_text_edges, root_node_id=root_node_id),
                session.execute_read(self._read_next_chunk_edges, root_node_id=root_node_id),
            )

    def knowledge_graph_exists(self, root_node_id: int) -> bool:
        """
        Check if the knowledge graph with specific root_node_id exists in the Neo4j database.

        Args:
            root_node_id (int): The node id of the root node.

        Returns:
            bool: True if the root node exists, False otherwise.
        """
        query = "MATCH (n {node_id: $root_node_id}) RETURN count(n) > 0 AS exists"
        with self.driver.session() as session:
            result = session.run(query, root_node_id=root_node_id)
            return result.single()["exists"]

    def count_nodes(self, tx: ManagedTransaction) -> int:
        """
        Return the number of nodes in the Neo4j database.

        Args:
            tx (ManagedTransaction): An active Neo4j transaction.

        Returns:
            int: The total number of nodes in the database.
        """
        query = """
          MATCH (n)
          RETURN count(n) as count
        """
        result = tx.run(query)
        return result.single()["count"]

    def verify_empty(self, tx: ManagedTransaction) -> bool:
        """Verify that the Neo4j database is empty."""
        return self.count_nodes(tx) == 0

    def clear_all_knowledge_graph(self):
        """Clear all knowledge graphs from neo4j."""
        query = """
      MATCH (n)
      DETACH DELETE n
    """
        self._logger.info("Deleting knowledge graph from neo4j")
        with self.driver.session() as session:
            session.run(query)

            max_retries = 3
            for attempt in range(max_retries):
                if session.execute_read(self.verify_empty):
                    break

                self._logger.warning(f"Database not empty after attempt {attempt + 1}, retrying...")
                session.run(query)

    def get_new_knowledge_graph_root_node_id(self) -> int:
        """
        Estimate the next available node id in the Neo4j database.

        Returns:
            int: The next available node id (max id + 1), or 0 if no nodes exist.
        """
        query = "MATCH (n) RETURN max(n.node_id) AS max_node_id"
        with self.driver.session() as session:
            result = session.run(query)
            max_node_id = result.single()["max_node_id"]
            return 0 if max_node_id is None else max_node_id + 1

    def clear_knowledge_graph(self, root_node_id: int):
        """
        Delete the subgraph rooted at root_node_id, including all descendant nodes and their relationships.

        Args:
            root_node_id (int): The node id of the root node.
        """
        query = """
        MATCH (root {node_id: $root_node_id})
        OPTIONAL MATCH (root)-[*]->(descendant)
        DETACH DELETE root, descendant
        """
        with self.driver.session() as session:
            session.run(query, root_node_id=root_node_id)
