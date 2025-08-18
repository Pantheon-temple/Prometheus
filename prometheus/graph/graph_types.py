"""Type definition for nodes and edges in the knowledge graph."""

import dataclasses
import enum
from typing import TypedDict, Union


@dataclasses.dataclass(frozen=True)
class FileNode:
    """A node representing a file/dir.

    Attributes:
      basename: The basename of a file/dir, like 'bar.py' or 'foo'.
      relative_path: The relative path from the root path, like 'foo/bar/baz.java'.
    """

    basename: str
    relative_path: str


@dataclasses.dataclass(frozen=True)
class ASTNode:
    """A node representing a tree-sitter node.

    Attributes:
      type: The tree-sitter node type.
      start_line: The starting line number. 0-indexed and inclusive.
      end_line: The ending line number.  0-indexed and inclusive.
      text: The source code correcpsonding to the node.
    """

    type: str
    start_line: int
    end_line: int
    text: str


@dataclasses.dataclass(frozen=True)
class TextNode:
    """A node representing a piece of text.

    Attributes:
      text: A string.
      metadata: The metadata about the string.
    """

    text: str
    metadata: str


@dataclasses.dataclass(frozen=True)
class KnowledgeGraphNode:
    """A node in the knowledge graph.

    Attributes:
      node_id: A id that uniquely identifies a node in the graph.
      node: The node itself, can be a FileNode, ASTNode or TextNode.
    """

    node_id: int
    node: Union[FileNode, ASTNode, TextNode]

    def to_neo4j_node(self) -> Union["Neo4jFileNode", "Neo4jASTNode", "Neo4jTextNode"]:
        """Convert the KnowledgeGraphNode into a Neo4j node format."""
        match self.node:
            case FileNode():
                return Neo4jFileNode(
                    node_id=self.node_id,
                    basename=self.node.basename,
                    relative_path=self.node.relative_path,
                )
            case ASTNode():
                return Neo4jASTNode(
                    node_id=self.node_id,
                    type=self.node.type,
                    start_line=self.node.start_line,
                    end_line=self.node.end_line,
                    text=self.node.text,
                )
            case TextNode():
                return Neo4jTextNode(
                    node_id=self.node_id,
                    text=self.node.text,
                    metadata=self.node.metadata,
                )
            case _:
                raise ValueError("Unknown KnowledgeGraphNode.node type")

    @classmethod
    def from_neo4j_file_node(cls, node: "Neo4jFileNode") -> "KnowledgeGraphNode":
        return cls(
            node_id=node["node_id"],
            node=FileNode(
                basename=node["basename"],
                relative_path=node["relative_path"],
            ),
        )

    @classmethod
    def from_neo4j_ast_node(cls, node: "Neo4jASTNode") -> "KnowledgeGraphNode":
        return cls(
            node_id=node["node_id"],
            node=ASTNode(
                type=node["type"],
                start_line=node["start_line"],
                end_line=node["end_line"],
                text=node["text"],
            ),
        )

    @classmethod
    def from_neo4j_text_node(cls, node: "Neo4jTextNode") -> "KnowledgeGraphNode":
        return cls(
            node_id=node["node_id"],
            node=TextNode(text=node["text"], metadata=node["metadata"]),
        )


class KnowledgeGraphEdgeType(enum.StrEnum):
    """Enum of all knowledge graph edge types"""

    parent_of = "PARENT_OF"  # ASTNode -> ASTNode
    has_file = "HAS_FILE"  # FileNode -> FileNode
    has_ast = "HAS_AST"  # FileNode -> ASTNode
    has_text = "HAS_TEXT"  # FileNode -> TextNode
    next_chunk = "NEXT_CHUNK"  # TextNode -> TextNode


@dataclasses.dataclass(frozen=True)
class KnowledgeGraphEdge:
    """An edge in the knowledge graph.

    Attributes:
      source: The source knowledge graph node.
      target: The target knowledge graph node.
      type: The knowledge graph edge type.
    """

    source: KnowledgeGraphNode
    target: KnowledgeGraphNode
    type: KnowledgeGraphEdgeType

    def to_neo4j_edge(
        self,
    ) -> Union[
        "Neo4jHasFileEdge",
        "Neo4jHasASTEdge",
        "Neo4jParentOfEdge",
        "Neo4jHasTextEdge",
        "Neo4jNextChunkEdge",
    ]:
        """Convert the KnowledgeGraphEdge into a Neo4j edge format."""
        match self.type:
            case KnowledgeGraphEdgeType.has_file:
                return Neo4jHasFileEdge(
                    source=self.source.to_neo4j_node(),
                    target=self.target.to_neo4j_node(),
                )
            case KnowledgeGraphEdgeType.has_ast:
                return Neo4jHasASTEdge(
                    source=self.source.to_neo4j_node(),
                    target=self.target.to_neo4j_node(),
                )
            case KnowledgeGraphEdgeType.parent_of:
                return Neo4jParentOfEdge(
                    source=self.source.to_neo4j_node(),
                    target=self.target.to_neo4j_node(),
                )
            case KnowledgeGraphEdgeType.has_text:
                return Neo4jHasTextEdge(
                    source=self.source.to_neo4j_node(),
                    target=self.target.to_neo4j_node(),
                )
            case KnowledgeGraphEdgeType.next_chunk:
                return Neo4jNextChunkEdge(
                    source=self.source.to_neo4j_node(),
                    target=self.target.to_neo4j_node(),
                )
            case _:
                raise ValueError(f"Unknown edge type: {self.type}")


###############################################################################
#                              Neo4j types                                    #
###############################################################################


class Neo4jMetadataNode(TypedDict):
    codebase_source: str
    local_path: str
    https_url: str
    commit_id: str


class Neo4jFileNode(TypedDict):
    node_id: int
    basename: str
    relative_path: str


class Neo4jASTNode(TypedDict):
    node_id: int
    type: str
    start_line: int
    end_line: int
    text: str


class Neo4jTextNode(TypedDict):
    node_id: int
    text: str
    metadata: str


class Neo4jHasFileEdge(TypedDict):
    source: Neo4jFileNode
    target: Neo4jFileNode


class Neo4jHasASTEdge(TypedDict):
    source: Neo4jFileNode
    target: Neo4jASTNode


class Neo4jParentOfEdge(TypedDict):
    source: Neo4jASTNode
    target: Neo4jASTNode


class Neo4jHasTextEdge(TypedDict):
    source: Neo4jFileNode
    target: Neo4jTextNode


class Neo4jNextChunkEdge(TypedDict):
    source: Neo4jTextNode
    target: Neo4jTextNode
