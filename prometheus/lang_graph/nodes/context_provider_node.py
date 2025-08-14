"""Knowledge graph-based context provider for codebase queries.

This module implements a specialized context provider that uses a Neo4j knowledge graph
to find relevant code context based on user queries. It leverages a language model
with structured tools to systematically search and analyze the codebase KnowledgeGraph.
"""

import functools
from typing import Dict

import neo4j
from langchain.tools import StructuredTool
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import SystemMessage

from prometheus.graph.knowledge_graph import KnowledgeGraph
from prometheus.tools import graph_traversal
from prometheus.utils.logger_manager import get_logger


class ContextProviderNode:
    """Provides contextual information from a codebase using knowledge graph search.

    This class implements a systematic approach to finding relevant code context
    by searching through a Neo4j knowledge graph representation of a codebase.
    It uses a combination of file structure navigation, AST analysis, and text
    search to gather comprehensive context for queries.

    The knowledge graph contains three main types of nodes:
    - FileNode: Represents files and directories
    - ASTNode: Represents syntactic elements from the code
    - TextNode: Represents documentation and text content
    """

    SYS_PROMPT = """\
You are a context gatherer that searches a Neo4j knowledge graph representation of a 
codebase. Your role is to understand the logic of the project and efficiently find relevant code and documentation 
context based on user queries.

Knowledge Graph Structure:
1. Node Types:
   - FileNode: Files and directories in the codebase
   - ASTNode: Abstract Syntax Tree nodes representing code structure
   - TextNode: Documentation, comments, and other text content

2. Core Relationships:
   - HAS_FILE: Directory → File relationships
   - HAS_AST: File → AST root node connection
   - HAS_TEXT: File → Text chunk linkage
   - PARENT_OF: AST node hierarchy
   - NEXT_CHUNK: Sequential text chunk connections

Search Strategy Guidelines:
1. Source Code Search:
   - Prioritize relative_path tools when exact file location is known
   - Fall back to basename tools for filename-only searches
   - Use AST node searches to find specific code structures
   - Use preview_* or read_* tools with more than hundred lines to get more context than class/function
   - If a search returns no results, try alternative approaches with broader scope

2. Documentation/Text Search:
   - Use find_text_node_* tools for docs and comments
   - Follow NEXT_CHUNK relationships for complete text using get_next_text_node_with_node_id
   - Search globally or scope to specific files as needed
   - Be flexible with search terms if initial attempts fail

3. Exploratory Search:
   - Start with find_file_node_* to verify paths
   - Use preview_file_content_* for quick content scanning
   - Use read_code_* tools to read more content beyond previews
   - Always have fallback strategies ready if primary search fails

4. Critical Rules:
   - Do not repeat the same query!

In your response, just provide a short summary with a few sentences (3-4 sentences) on what you have done.
As your searched are automatically visible to the user, you do not need to repeat them. 

The file tree of the codebase:
{file_tree}

Available AST node types for code structure search: {ast_node_types}
"""

    def __init__(
        self,
        model: BaseChatModel,
        kg: KnowledgeGraph,
        neo4j_driver: neo4j.Driver,
        max_token_per_result: int,
    ):
        """Initializes the ContextProviderNode with model, knowledge graph, and database connection.

        Sets up the context provider with necessary prompts, graph traversal tools,
        and logging configuration. Initializes the system prompt with the current
        file tree structure from the knowledge graph.

        Args:
          model: Language model instance that will be used for query analysis and
            context finding. Must be a BaseChatModel implementation that supports
            tool binding.
          kg: Knowledge graph instance containing the processed codebase structure.
            Used to obtain the file tree for system prompts.
          neo4j_driver: Neo4j driver instance for executing graph queries. This
            driver should be properly configured with authentication and
            connection details.
          max_token_per_result: Maximum number of tokens per retrieved Neo4j result.
        """
        self.neo4j_driver = neo4j_driver
        self.max_token_per_result = max_token_per_result

        ast_node_types_str = ", ".join(kg.get_all_ast_node_types())
        self.system_prompt = SystemMessage(
            self.SYS_PROMPT.format(file_tree=kg.get_file_tree(), ast_node_types=ast_node_types_str)
        )
        self.tools = self._init_tools()
        self.model_with_tools = model.bind_tools(self.tools)

        self._logger = get_logger(__name__)

    def _init_tools(self):
        """
        Initializes KnowledgeGraph traversal tools.

        Returns:
          List of StructuredTool instances configured for KnowledgeGraph traversal.
        """
        tools = []

        # === FILE SEARCH TOOLS ===

        # Tool: Find file node by filename (basename)
        # Used when only the filename (not full path) is known
        find_file_node_with_basename_fn = functools.partial(
            graph_traversal.find_file_node_with_basename,
            driver=self.neo4j_driver,
            max_token_per_result=self.max_token_per_result,
        )
        find_file_node_with_basename_tool = StructuredTool.from_function(
            func=find_file_node_with_basename_fn,
            name=graph_traversal.find_file_node_with_basename.__name__,
            description=graph_traversal.FIND_FILE_NODE_WITH_BASENAME_DESCRIPTION,
            args_schema=graph_traversal.FindFileNodeWithBasenameInput,
            response_format="content_and_artifact",
        )
        tools.append(find_file_node_with_basename_tool)

        # Tool: Find file node by relative path
        # Preferred method when the exact file path is known
        find_file_node_with_relative_path_fn = functools.partial(
            graph_traversal.find_file_node_with_relative_path,
            driver=self.neo4j_driver,
            max_token_per_result=self.max_token_per_result,
        )
        find_file_node_with_relative_path_tool = StructuredTool.from_function(
            func=find_file_node_with_relative_path_fn,
            name=graph_traversal.find_file_node_with_relative_path.__name__,
            description=graph_traversal.FIND_FILE_NODE_WITH_RELATIVE_PATH_DESCRIPTION,
            args_schema=graph_traversal.FindFileNodeWithRelativePathInput,
            response_format="content_and_artifact",
        )
        tools.append(find_file_node_with_relative_path_tool)

        # === AST NODE SEARCH TOOLS ===

        # Tool: Find AST node by text match in file (by basename)
        # Useful for searching specific snippets or patterns in unknown locations
        find_ast_node_with_text_in_file_with_basename_fn = functools.partial(
            graph_traversal.find_ast_node_with_text_in_file_with_basename,
            driver=self.neo4j_driver,
            max_token_per_result=self.max_token_per_result,
        )
        find_ast_node_with_text_in_file_with_basename_tool = StructuredTool.from_function(
            func=find_ast_node_with_text_in_file_with_basename_fn,
            name=graph_traversal.find_ast_node_with_text_in_file_with_basename.__name__,
            description=graph_traversal.FIND_AST_NODE_WITH_TEXT_IN_FILE_WITH_BASENAME_DESCRIPTION,
            args_schema=graph_traversal.FindASTNodeWithTextInFileWithBasenameInput,
            response_format="content_and_artifact",
        )
        tools.append(find_ast_node_with_text_in_file_with_basename_tool)

        # Tool: Find AST node by text match in file (by relative path)
        find_ast_node_with_text_in_file_with_relative_path_fn = functools.partial(
            graph_traversal.find_ast_node_with_text_in_file_with_relative_path,
            driver=self.neo4j_driver,
            max_token_per_result=self.max_token_per_result,
        )
        find_ast_node_with_text_in_file_with_relative_path_tool = StructuredTool.from_function(
            func=find_ast_node_with_text_in_file_with_relative_path_fn,
            name=graph_traversal.find_ast_node_with_text_in_file_with_relative_path.__name__,
            description=graph_traversal.FIND_AST_NODE_WITH_TEXT_IN_FILE_WITH_RELATIVE_PATH_DESCRIPTION,
            args_schema=graph_traversal.FindASTNodeWithTextInFileWithRelativePathInput,
            response_format="content_and_artifact",
        )
        tools.append(find_ast_node_with_text_in_file_with_relative_path_tool)

        # Tool: Find AST node by type in file (by basename)
        # Example types: FunctionDef, ClassDef, Assign, etc.
        find_ast_node_with_type_in_file_with_basename_fn = functools.partial(
            graph_traversal.find_ast_node_with_type_in_file_with_basename,
            driver=self.neo4j_driver,
            max_token_per_result=self.max_token_per_result,
        )
        find_ast_node_with_type_in_file_with_basename_tool = StructuredTool.from_function(
            func=find_ast_node_with_type_in_file_with_basename_fn,
            name=graph_traversal.find_ast_node_with_type_in_file_with_basename.__name__,
            description=graph_traversal.FIND_AST_NODE_WITH_TYPE_IN_FILE_WITH_BASENAME_DESCRIPTION,
            args_schema=graph_traversal.FindASTNodeWithTypeInFileWithBasenameInput,
            response_format="content_and_artifact",
        )
        tools.append(find_ast_node_with_type_in_file_with_basename_tool)

        # Tool: Find AST node by type in file (by relative path)
        find_ast_node_with_type_in_file_with_relative_path_fn = functools.partial(
            graph_traversal.find_ast_node_with_type_in_file_with_relative_path,
            driver=self.neo4j_driver,
            max_token_per_result=self.max_token_per_result,
        )
        find_ast_node_with_type_in_file_with_relative_path_tool = StructuredTool.from_function(
            func=find_ast_node_with_type_in_file_with_relative_path_fn,
            name=graph_traversal.find_ast_node_with_type_in_file_with_relative_path.__name__,
            description=graph_traversal.FIND_AST_NODE_WITH_TYPE_IN_FILE_WITH_RELATIVE_PATH_DESCRIPTION,
            args_schema=graph_traversal.FindASTNodeWithTypeInFileWithRelativePathInput,
            response_format="content_and_artifact",
        )
        tools.append(find_ast_node_with_type_in_file_with_relative_path_tool)

        # === TEXT/DOCUMENT SEARCH TOOLS ===

        # Tool: Find text node globally by keyword
        find_text_node_with_text_fn = functools.partial(
            graph_traversal.find_text_node_with_text,
            driver=self.neo4j_driver,
            max_token_per_result=self.max_token_per_result,
        )
        find_text_node_with_text_tool = StructuredTool.from_function(
            func=find_text_node_with_text_fn,
            name=graph_traversal.find_text_node_with_text.__name__,
            description=graph_traversal.FIND_TEXT_NODE_WITH_TEXT_DESCRIPTION,
            args_schema=graph_traversal.FindTextNodeWithTextInput,
            response_format="content_and_artifact",
        )
        tools.append(find_text_node_with_text_tool)

        # Tool: Find text node by keyword in specific file
        find_text_node_with_text_in_file_fn = functools.partial(
            graph_traversal.find_text_node_with_text_in_file,
            driver=self.neo4j_driver,
            max_token_per_result=self.max_token_per_result,
        )
        find_text_node_with_text_in_file_tool = StructuredTool.from_function(
            func=find_text_node_with_text_in_file_fn,
            name=graph_traversal.find_text_node_with_text_in_file.__name__,
            description=graph_traversal.FIND_TEXT_NODE_WITH_TEXT_IN_FILE_DESCRIPTION,
            args_schema=graph_traversal.FindTextNodeWithTextInFileInput,
            response_format="content_and_artifact",
        )
        tools.append(find_text_node_with_text_in_file_tool)

        # Tool: Fetch the next text node chunk in a chain (used for long docs/comments)
        get_next_text_node_with_node_id_fn = functools.partial(
            graph_traversal.get_next_text_node_with_node_id,
            driver=self.neo4j_driver,
            max_token_per_result=self.max_token_per_result,
        )
        get_next_text_node_with_node_id_tool = StructuredTool.from_function(
            func=get_next_text_node_with_node_id_fn,
            name=graph_traversal.get_next_text_node_with_node_id.__name__,
            description=graph_traversal.GET_NEXT_TEXT_NODE_WITH_NODE_ID_DESCRIPTION,
            args_schema=graph_traversal.GetNextTextNodeWithNodeIdInput,
            response_format="content_and_artifact",
        )
        tools.append(get_next_text_node_with_node_id_tool)

        # === FILE PREVIEW & READING TOOLS ===

        # Tool: Preview contents of file by basename
        preview_file_content_with_basename_fn = functools.partial(
            graph_traversal.preview_file_content_with_basename,
            driver=self.neo4j_driver,
            max_token_per_result=self.max_token_per_result,
        )
        preview_file_content_with_basename_tool = StructuredTool.from_function(
            func=preview_file_content_with_basename_fn,
            name=graph_traversal.preview_file_content_with_basename.__name__,
            description=graph_traversal.PREVIEW_FILE_CONTENT_WITH_BASENAME_DESCRIPTION,
            args_schema=graph_traversal.PreviewFileContentWithBasenameInput,
            response_format="content_and_artifact",
        )
        tools.append(preview_file_content_with_basename_tool)

        # Tool: Preview contents of file by relative path
        preview_file_content_with_relative_path_fn = functools.partial(
            graph_traversal.preview_file_content_with_relative_path,
            driver=self.neo4j_driver,
            max_token_per_result=self.max_token_per_result,
        )
        preview_file_content_with_relative_path_tool = StructuredTool.from_function(
            func=preview_file_content_with_relative_path_fn,
            name=graph_traversal.preview_file_content_with_relative_path.__name__,
            description=graph_traversal.PREVIEW_FILE_CONTENT_WITH_RELATIVE_PATH_DESCRIPTION,
            args_schema=graph_traversal.PreviewFileContentWithRelativePathInput,
            response_format="content_and_artifact",
        )
        tools.append(preview_file_content_with_relative_path_tool)

        # Tool: Read entire code file by basename
        read_code_with_basename_fn = functools.partial(
            graph_traversal.read_code_with_basename,
            driver=self.neo4j_driver,
            max_token_per_result=self.max_token_per_result,
        )
        read_code_with_basename_tool = StructuredTool.from_function(
            func=read_code_with_basename_fn,
            name=graph_traversal.read_code_with_basename.__name__,
            description=graph_traversal.READ_CODE_WITH_BASENAME_DESCRIPTION,
            args_schema=graph_traversal.ReadCodeWithBasenameInput,
            response_format="content_and_artifact",
        )
        tools.append(read_code_with_basename_tool)

        # Tool: Read entire code file by relative path
        read_code_with_relative_path_fn = functools.partial(
            graph_traversal.read_code_with_relative_path,
            driver=self.neo4j_driver,
            max_token_per_result=self.max_token_per_result,
        )
        read_code_with_relative_path_tool = StructuredTool.from_function(
            func=read_code_with_relative_path_fn,
            name=graph_traversal.read_code_with_relative_path.__name__,
            description=graph_traversal.READ_CODE_WITH_RELATIVE_PATH_DESCRIPTION,
            args_schema=graph_traversal.ReadCodeWithRelativePathInput,
            response_format="content_and_artifact",
        )
        tools.append(read_code_with_relative_path_tool)

        return tools

    def __call__(self, state: Dict):
        """Processes the current state and traverse the knowledge graph to retrieve context.

        Args:
          state: Current state containing the human query and previous context_messages.

        Returns:
          Dictionary that will update the state with the model's response messages.
        """
        # self._logger.debug(f"Context provider messages: {state['context_provider_messages']}")
        message_history = [self.system_prompt] + state["context_provider_messages"]
        response = self.model_with_tools.invoke(message_history)
        self._logger.debug(response)
        # The response will be added to the bottom of the list
        return {"context_provider_messages": [response]}
