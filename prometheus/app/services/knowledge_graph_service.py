"""Service for managing and interacting with Knowledge Graphs in Neo4j."""

import asyncio
from pathlib import Path

from prometheus.app.services.base_service import BaseService
from prometheus.app.services.neo4j_service import Neo4jService
from prometheus.graph.knowledge_graph import KnowledgeGraph
from prometheus.neo4j import knowledge_graph_handler


class KnowledgeGraphService(BaseService):
    """Manages the lifecycle and operations of Knowledge Graphs.

    This service handles the creation, persistence, and management of Knowledge Graphs
    that represent the whole codebase structures. It provides capabilities for building graphs
    from codebase, storing them in Neo4j, and managing their lifecycle.
    """

    def __init__(
        self,
        neo4j_service: Neo4jService,
        neo4j_batch_size: int,
        max_ast_depth: int,
        chunk_size: int,
        chunk_overlap: int,
    ):
        """Initializes the Knowledge Graph service.

        Args:
          neo4j_service: Service providing Neo4j database access.
          neo4j_batch_size: Number of nodes to process in each Neo4j batch operation.
          max_ast_depth: Maximum depth to traverse when building AST representations.
          chunk_size: Chunk size for processing text files.
          chunk_overlap: Overlap size for processing text files.
        """
        self.kg_handler = knowledge_graph_handler.KnowledgeGraphHandler(
            neo4j_service.neo4j_driver, neo4j_batch_size
        )
        self.max_ast_depth = max_ast_depth
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.writing_lock = asyncio.Lock()

    async def build_and_save_knowledge_graph(self, path: Path) -> int:
        """Builds a new Knowledge Graph from source code and saves it to Neo4j.

        Creates a new Knowledge Graph representation of the codebase at the specified path,
        optionally associating it with a repository URL and commit. Any existing
        Knowledge Graph will be cleared before building the new one.

        Args:
            path: Path to the source code directory to analyze.
        Returns:
            The root node ID of the newly created Knowledge Graph.
        """
        async with self.writing_lock:  # Ensure only one build operation at a time
            root_node_id = self.kg_handler.get_new_knowledge_graph_root_node_id()
            kg = KnowledgeGraph(
                self.max_ast_depth, self.chunk_size, self.chunk_overlap, root_node_id
            )
            await kg.build_graph(path)
            self.kg_handler.write_knowledge_graph(kg)
            return kg.root_node_id

    def clear_kg(self, root_node_id: int):
        self.kg_handler.clear_knowledge_graph(root_node_id)

    def get_knowledge_graph(
        self,
        root_node_id: int,
        max_ast_depth: int,
        chunk_size: int,
        chunk_overlap: int,
    ) -> KnowledgeGraph:
        return self.kg_handler.read_knowledge_graph(
            root_node_id, max_ast_depth, chunk_size, chunk_overlap
        )
