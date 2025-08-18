from sqlmodel import Field, SQLModel


class Repository(SQLModel, table=True):
    id: int = Field(primary_key=True, description="ID")
    url: str = Field(
        index=True,
        max_length=200,
        description="The URL of the repository.",
    )
    commit_id: str = Field(
        index=True,
        nullable=True,
        min_length=40,
        max_length=40,
        description="The commit id of the repository.",
    )
    playground_path: str = Field(
        unique=True,
        max_length=300,
        description="The playground path of the repository where the repository was cloned.",
    )
    is_working: bool = Field(
        default=False,
        description="Indicates whether the repository is currently being used for processing or not.",
    )
    user_id: int = Field(
        index=True, nullable=True, description="The ID of the user who upload this repository."
    )
    kg_root_node_id: int = Field(
        index=True, unique=True, description="The ID of the root node of the knowledge graph."
    )
    kg_max_ast_depth: int = Field(description="The maximum AST depth of the knowledge graph.")
    kg_chunk_size: int = Field(
        description="The size of the chunks used in the knowledge graph.",
    )
    kg_chunk_overlap: int = Field(
        description="The overlap of the chunks used in the knowledge graph."
    )
