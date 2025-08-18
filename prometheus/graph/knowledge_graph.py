"""The in-memory knowledge graph representation of a codebase.

In the knowledge graph, we have the following node types:
* FileNode: Represent a file/dir
* ASTNode: Represent a tree-sitter node
* TextNode: Represent a string

and the following edge types:
* HAS_FILE: Relationship between two FileNode, if one FileNode is the parent dir of another FileNode.
* HAS_AST: Relationship between FileNode and ASTNode, if the ASTNode is the root AST node for FileNode.
* HAS_TEXT: Relationship between FileNode and TextNode, if the TextNode is a chunk of text from FileNode.
* PARENT_OF: Relationship between two ASTNode, if one ASTNode is the parent of another ASTNode.
* NEXT_CHUNK: Relationship between two TextNode, if one TextNode is the next chunk of text of another TextNode.

In this way, we have all the directory structure, source code, and text information in a single knowledge graph.
This knowledge graph will be persisted in a graph database (neo4j), where an AI can use it to traverse the
codebase to find the most relevant context for the user query.
"""

import asyncio
import itertools
import logging
from collections import defaultdict, deque
from pathlib import Path
from typing import Mapping, Optional, Sequence

import igittigitt

from prometheus.graph.file_graph_builder import FileGraphBuilder
from prometheus.graph.graph_types import (
    ASTNode,
    FileNode,
    KnowledgeGraphEdge,
    KnowledgeGraphEdgeType,
    KnowledgeGraphNode,
    Neo4jASTNode,
    Neo4jFileNode,
    Neo4jHasASTEdge,
    Neo4jHasFileEdge,
    Neo4jHasTextEdge,
    Neo4jNextChunkEdge,
    Neo4jParentOfEdge,
    Neo4jTextNode,
    TextNode,
)


class KnowledgeGraph:
    def __init__(
        self,
        max_ast_depth: int,
        chunk_size: int,
        chunk_overlap: int,
        root_node_id: int,
        root_node: Optional[KnowledgeGraphNode] = None,
        knowledge_graph_nodes: Optional[Sequence[KnowledgeGraphNode]] = None,
        knowledge_graph_edges: Optional[Sequence[KnowledgeGraphEdge]] = None,
    ):
        """Initializes the knowledge graph.

        Args:
          max_ast_depth: The maximum depth of tree-sitter nodes to parse.
          chunk_size: The chunk size for text files.
          chunk_overlap: The overlap size for text files.
          root_node_id: The root_node_id.
          root_node: The root node for the knowledge graph.
          knowledge_graph_nodes: The initial list of knowledge graph nodes.
          knowledge_graph_edges: The initial list of knowledge graph edges.
        """
        self.max_ast_depth = max_ast_depth
        self.root_node_id = root_node_id
        self._root_node = root_node
        self._knowledge_graph_nodes = (
            knowledge_graph_nodes if knowledge_graph_nodes is not None else []
        )
        self._knowledge_graph_edges = (
            knowledge_graph_edges if knowledge_graph_edges is not None else []
        )
        self._next_node_id = root_node_id + len(self._knowledge_graph_nodes)

        self._file_graph_builder = FileGraphBuilder(max_ast_depth, chunk_size, chunk_overlap)
        self._logger = logging.getLogger("prometheus.graph.knowledge_graph")

    async def build_graph(self, root_dir: Path):
        """Asynchronously builds knowledge graph for a codebase at a location.

        Args:
            root_dir: The codebase root directory.
        """
        await asyncio.to_thread(self._build_graph, root_dir)

    def _build_graph(self, root_dir: Path):
        """Builds knowledge graph for a codebase at a location.

        Args:
            root_dir: The codebase root directory.
        """
        root_dir = root_dir.absolute()
        gitignore_parser = igittigitt.IgnoreParser()
        gitignore_parser.parse_rule_files(root_dir)
        gitignore_parser.add_rule(".git", root_dir)

        # The root node for the whole graph
        root_dir_node = FileNode(basename=root_dir.name, relative_path=".")
        kg_root_dir_node = KnowledgeGraphNode(self._next_node_id, root_dir_node)
        self._next_node_id += 1
        self._knowledge_graph_nodes.append(kg_root_dir_node)
        self._root_node = kg_root_dir_node

        file_stack = deque()
        file_stack.append((root_dir, kg_root_dir_node))

        # Now we traverse the file system to parse all the files and create all relationships
        while file_stack:
            file, kg_file_path_node = file_stack.pop()

            # If the file is a directory, we create FileNode for all supported children files.
            if file.is_dir():
                self._logger.info(f"Processing directory {file}")
                for child_file in sorted(file.iterdir()):
                    # Skip if the child is not a file or it is not supported by the file graph builder.
                    if child_file.is_file() and not self._file_graph_builder.supports_file(
                        child_file
                    ):
                        self._logger.info(f"Skip parsing {child_file} because it is not supported")
                        continue

                    if gitignore_parser.match(child_file):
                        self._logger.info(f"Skipping {child_file} because it is ignored")
                        continue

                    child_file_node = FileNode(
                        basename=child_file.name,
                        relative_path=child_file.relative_to(root_dir).as_posix(),
                    )
                    kg_child_file_node = KnowledgeGraphNode(self._next_node_id, child_file_node)
                    self._next_node_id += 1
                    self._knowledge_graph_nodes.append(kg_child_file_node)
                    self._knowledge_graph_edges.append(
                        KnowledgeGraphEdge(
                            kg_file_path_node,
                            kg_child_file_node,
                            KnowledgeGraphEdgeType.has_file,
                        )
                    )

                    file_stack.append((child_file, kg_child_file_node))
            # Process the file otherwise.
            else:
                self._logger.info(f"Processing file {file}")
                try:
                    next_node_id, kg_nodes, kg_edges = self._file_graph_builder.build_file_graph(
                        kg_file_path_node, file, self._next_node_id
                    )
                except UnicodeDecodeError:
                    self._logger.warning(f"UnicodeDecodeError when processing {file}")
                    continue
                self._next_node_id = next_node_id
                self._knowledge_graph_nodes.extend(kg_nodes)
                self._knowledge_graph_edges.extend(kg_edges)

    @classmethod
    def from_neo4j(
        cls,
        root_node_id: int,
        max_ast_depth: int,
        chunk_size: int,
        chunk_overlap: int,
        file_nodes: Sequence[KnowledgeGraphNode],
        ast_nodes: Sequence[KnowledgeGraphNode],
        text_nodes: Sequence[KnowledgeGraphNode],
        parent_of_edges_ids: Sequence[Mapping[str, int]],
        has_file_edges_ids: Sequence[Mapping[str, int]],
        has_ast_edges_ids: Sequence[Mapping[str, int]],
        has_text_edges_ids: Sequence[Mapping[str, int]],
        next_chunk_edges_ids: Sequence[Mapping[str, int]],
    ):
        """Creates a knowledge graph from nodes and edges stored in neo4j."""
        # All nodes
        knowledge_graph_nodes = [x for x in itertools.chain(file_nodes, ast_nodes, text_nodes)]

        # All edges
        node_id_to_node = {x.node_id: x for x in knowledge_graph_nodes}
        parent_of_edges = [
            KnowledgeGraphEdge(
                node_id_to_node[parent_of_edge_ids["source_id"]],
                node_id_to_node[parent_of_edge_ids["target_id"]],
                KnowledgeGraphEdgeType.parent_of,
            )
            for parent_of_edge_ids in parent_of_edges_ids
        ]
        has_file_edges = [
            KnowledgeGraphEdge(
                node_id_to_node[has_file_edge_ids["source_id"]],
                node_id_to_node[has_file_edge_ids["target_id"]],
                KnowledgeGraphEdgeType.has_file,
            )
            for has_file_edge_ids in has_file_edges_ids
        ]
        has_ast_edges = [
            KnowledgeGraphEdge(
                node_id_to_node[has_ast_edge_ids["source_id"]],
                node_id_to_node[has_ast_edge_ids["target_id"]],
                KnowledgeGraphEdgeType.has_ast,
            )
            for has_ast_edge_ids in has_ast_edges_ids
        ]
        has_text_edges = [
            KnowledgeGraphEdge(
                node_id_to_node[has_text_edge_ids["source_id"]],
                node_id_to_node[has_text_edge_ids["target_id"]],
                KnowledgeGraphEdgeType.has_text,
            )
            for has_text_edge_ids in has_text_edges_ids
        ]
        next_chunk_edges = [
            KnowledgeGraphEdge(
                node_id_to_node[next_chunk_edge_ids["source_id"]],
                node_id_to_node[next_chunk_edge_ids["target_id"]],
                KnowledgeGraphEdgeType.next_chunk,
            )
            for next_chunk_edge_ids in next_chunk_edges_ids
        ]
        knowledge_graph_edges = [
            x
            for x in itertools.chain(
                parent_of_edges, has_file_edges, has_ast_edges, has_text_edges, next_chunk_edges
            )
        ]

        # Root node
        root_node = None
        for node in knowledge_graph_nodes:
            if node.node_id == root_node_id:
                root_node = node
                break
        if root_node is None:
            raise ValueError(f"Node with node_id {root_node_id} not found.")

        return cls(
            max_ast_depth=max_ast_depth,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            root_node_id=root_node_id,
            root_node=root_node,
            knowledge_graph_nodes=knowledge_graph_nodes,
            knowledge_graph_edges=knowledge_graph_edges,
        )

    def get_file_tree(self, max_depth: int = 5, max_lines: int = 5000) -> str:
        """Generate a tree-like string representation of the file structure.

        Creates an ASCII tree visualization of the file hierarchy, similar to the Unix 'tree'
        command output. The tree is generated using Unicode box-drawing characters and
        indentation to show the hierarchical relationship between files and directories.

        Example:
          project/
          ├── src/
          │   ├── main.py
          │   └── utils/
          │       ├── helpers.py
          │       └── config.py
          └── tests/
              ├── test_main.py
              └── test_utils.py

        Args:
          max_depth: Maximum depth of the tree to display. Nodes beyond this depth will
            be omitted. Default to 5.
          max_lines: Maximum number of lines in the output string. Useful for truncating
            very large trees. Default to 5000.

        Returns:
          str: A string representation of the file tree, where each line represents a file
              or directory, with appropriate indentation and connecting lines showing
              the hierarchy.

        Algorithm:
            - Uses a stack-based depth-first traversal to walk the file tree.
            - Maintains a prefix string to build up the correct indentation and connectors.
            - For each node, determines whether it is the last child in its directory to use
              the correct tree connector (├── or └──).
            - Accumulates results in `result_lines` until either max_depth or max_lines is reached.
        """
        file_node_adjacency_dict = (
            self._get_file_node_adjacency_dict()
        )  # Maps nodes to their children

        # Each stack entry contains: (current_node, depth, prefix_string, is_last_child)
        stack = deque()
        stack.append((self._root_node, 0, "", None))
        result_lines = []

        # Box-drawing characters and indentation constants
        SPACE = "    "  # Indentation for levels without children
        BRANCH = "|   "  # Vertical line for intermediate children
        TEE = "├── "  # Entry for a non-final child
        LAST = "└── "  # Entry for the last child

        while stack and (len(result_lines)) < max_lines:
            file_node, depth, prefix, is_last = stack.pop()

            # Skip if we've exceeded max_depth
            if depth > max_depth:
                continue

            # Choose the connector character depending on whether this is the last child
            pointer = LAST if is_last else TEE
            line_prefix = "" if depth == 0 else prefix + pointer

            # Add the current file or directory to the result lines
            result_lines.append(line_prefix + file_node.node.basename)

            # Get the current node's children and sort them alphabetically by name
            sorted_children_file_node = sorted(
                file_node_adjacency_dict[file_node], key=lambda x: x.node.basename
            )

            # Traverse the children in reverse order to maintain the correct tree shape
            for i in range(len(sorted_children_file_node) - 1, -1, -1):
                extension = SPACE if is_last else BRANCH  # Update prefix for children
                new_prefix = "" if depth == 0 else prefix + extension
                stack.append(
                    (
                        sorted_children_file_node[i],
                        depth + 1,
                        new_prefix,
                        i == len(sorted_children_file_node) - 1,  # True if last child
                    )
                )

        # Join all lines into a single string for output
        return "\n".join(result_lines)

    def get_all_ast_node_types(self) -> Sequence[str]:
        ast_node_types = set()
        for ast_node in self.get_ast_nodes():
            ast_node_types.add(ast_node.node.type)
        return list(ast_node_types)

    def _get_file_node_adjacency_dict(
        self,
    ) -> Mapping[KnowledgeGraphNode, Sequence[KnowledgeGraphNode]]:
        file_node_adjacency_dict = defaultdict(list)
        for has_file_edge in self.get_has_file_edges():
            file_node_adjacency_dict[has_file_edge.source].append(has_file_edge.target)
        return file_node_adjacency_dict

    def get_file_nodes(self) -> Sequence[KnowledgeGraphNode]:
        return [
            kg_node for kg_node in self._knowledge_graph_nodes if isinstance(kg_node.node, FileNode)
        ]

    def get_ast_nodes(self) -> Sequence[KnowledgeGraphNode]:
        return [
            kg_node for kg_node in self._knowledge_graph_nodes if isinstance(kg_node.node, ASTNode)
        ]

    def get_text_nodes(self) -> Sequence[KnowledgeGraphNode]:
        return [
            kg_node for kg_node in self._knowledge_graph_nodes if isinstance(kg_node.node, TextNode)
        ]

    def get_has_ast_edges(self) -> Sequence[KnowledgeGraphEdge]:
        return [
            kg_edge
            for kg_edge in self._knowledge_graph_edges
            if kg_edge.type == KnowledgeGraphEdgeType.has_ast
        ]

    def get_has_file_edges(self) -> Sequence[KnowledgeGraphEdge]:
        return [
            kg_edge
            for kg_edge in self._knowledge_graph_edges
            if kg_edge.type == KnowledgeGraphEdgeType.has_file
        ]

    def get_has_text_edges(self) -> Sequence[KnowledgeGraphEdge]:
        return [
            kg_edge
            for kg_edge in self._knowledge_graph_edges
            if kg_edge.type == KnowledgeGraphEdgeType.has_text
        ]

    def get_next_chunk_edges(self) -> Sequence[KnowledgeGraphEdge]:
        return [
            kg_edge
            for kg_edge in self._knowledge_graph_edges
            if kg_edge.type == KnowledgeGraphEdgeType.next_chunk
        ]

    def get_parent_of_edges(self) -> Sequence[KnowledgeGraphEdge]:
        return [
            kg_edge
            for kg_edge in self._knowledge_graph_edges
            if kg_edge.type == KnowledgeGraphEdgeType.parent_of
        ]

    def get_neo4j_file_nodes(self) -> Sequence[Neo4jFileNode]:
        return [kg_node.to_neo4j_node() for kg_node in self.get_file_nodes()]

    def get_neo4j_ast_nodes(self) -> Sequence[Neo4jASTNode]:
        return [kg_node.to_neo4j_node() for kg_node in self.get_ast_nodes()]

    def get_neo4j_text_nodes(self) -> Sequence[Neo4jTextNode]:
        return [kg_node.to_neo4j_node() for kg_node in self.get_text_nodes()]

    def get_neo4j_has_ast_edges(self) -> Sequence[Neo4jHasASTEdge]:
        return [kg_edge.to_neo4j_edge() for kg_edge in self.get_has_ast_edges()]

    def get_neo4j_has_file_edges(self) -> Sequence[Neo4jHasFileEdge]:
        return [kg_edge.to_neo4j_edge() for kg_edge in self.get_has_file_edges()]

    def get_neo4j_has_text_edges(self) -> Sequence[Neo4jHasTextEdge]:
        return [kg_edge.to_neo4j_edge() for kg_edge in self.get_has_text_edges()]

    def get_neo4j_next_chunk_edges(self) -> Sequence[Neo4jNextChunkEdge]:
        return [kg_edge.to_neo4j_edge() for kg_edge in self.get_next_chunk_edges()]

    def get_neo4j_parent_of_edges(self) -> Sequence[Neo4jParentOfEdge]:
        return [kg_edge.to_neo4j_edge() for kg_edge in self.get_parent_of_edges()]

    def __eq__(self, other: "KnowledgeGraph") -> bool:
        if not isinstance(other, KnowledgeGraph):
            return False

        self._knowledge_graph_nodes.sort(key=lambda x: x.node_id)
        other._knowledge_graph_nodes.sort(key=lambda x: x.node_id)

        for self_kg_node, other_kg_node in itertools.zip_longest(
            self._knowledge_graph_nodes, other._knowledge_graph_nodes, fillvalue=None
        ):
            if self_kg_node != other_kg_node:
                return False

        self._knowledge_graph_edges.sort(key=lambda x: (x.source.node_id, x.target.node_id, x.type))
        other._knowledge_graph_edges.sort(
            key=lambda x: (x.source.node_id, x.target.node_id, x.type)
        )
        for self_kg_edge, other_kg_edge in itertools.zip_longest(
            self._knowledge_graph_edges, other._knowledge_graph_edges, fillvalue=None
        ):
            if self_kg_edge != other_kg_edge:
                return False

        return True
