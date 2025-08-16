from pathlib import Path
from typing import Any, Mapping, Sequence, Union
from dataclasses import dataclass

from neo4j import GraphDatabase
from pydantic import BaseModel, Field

from prometheus.parser import tree_sitter_parser
from prometheus.utils import neo4j_util
from prometheus.utils.str_util import pre_append_line_numbers

MAX_RESULT = 30

"""
Tools for retrieving nodes from the Neo4j graph database.
These tools allow you to search for FileNode, ASTNode, and TextNode based on various attributes
like basename, relative path, text content, and node type.

A content and an artifact will be returned.
The content is a string representation of the node(s) found, and the artifact is a list of dictionaries
"""

@dataclass
class ToolSpec:
    description: str
    input_schema: type


class FindFileNodeWithBasenameInput(BaseModel):
    basename: str = Field("The basename of FileNode to search for")

class FindFileNodeWithRelativePathInput(BaseModel):
    relative_path: str = Field("The relative_path of FileNode to search for")

class FindASTNodeWithTextInFileWithBasenameInput(BaseModel):
    text: str = Field("Search ASTNode that exactly contains this text.")
    basename: str = Field("The basename of file/directory to search under for ASTNodes.")

class FindASTNodeWithTextInFileWithRelativePathInput(BaseModel):
    text: str = Field("Search ASTNode that exactly contains this text.")
    relative_path: str = Field("The relative path of file/directory to search under for ASTNodes.")

class FindASTNodeWithTypeInFileWithBasenameInput(BaseModel):
    type: str = Field("Search ASTNode with this tree-sitter node type.")
    basename: str = Field("The basename of file/directory to search under for ASTNodes.")

class FindASTNodeWithTypeInFileWithRelativePathInput(BaseModel):
    type: str = Field("Search ASTNode with this tree-sitter node type.")
    relative_path: str = Field("The relative path of file/directory to search under for ASTNodes.")

class FindTextNodeWithTextInput(BaseModel):
    text: str = Field("Search TextNode that exactly contains this text.")

class FindTextNodeWithTextInFileInput(BaseModel):
    text: str = Field("Search TextNode that exactly contains this text.")
    basename: str = Field("The basename of FileNode to search TextNode.")

class GetNextTextNodeWithNodeIdInput(BaseModel):
    node_id: int = Field("Get the next TextNode of this given node_id.")

class PreviewFileContentWithBasenameInput(BaseModel):
    basename: str = Field("The basename of FileNode to preview.")

class PreviewFileContentWithRelativePathInput(BaseModel):
    relative_path: str = Field("The relative path of FileNode to preview.")

class ReadCodeWithBasenameInput(BaseModel):
    basename: str = Field("The basename of FileNode to read.")
    start_line: int = Field("The starting line number, 1-indexed and inclusive.")
    end_line: int = Field("The ending line number, 1-indexed and exclusive.") 

class ReadCodeWithRelativePathInput(BaseModel):
    relative_path: str = Field("The relative path of FileNode to read from root of codebase.")
    start_line: int = Field("The starting line number, 1-indexed and inclusive.")
    end_line: int = Field("The ending line number, 1-indexed and exclusive.")


class GraphTraversalTool:

    # FileNode retrieval tools
    find_file_node_with_basename_spec = ToolSpec(
        description="""Find all FileNode in the graph with this basename of a file/dir. The basename must
        include the extension, like 'bar.py', 'baz.java' or 'foo'
        (in this case foo is a directory or a file without extension).

        You can use this tool to check if a file/dir with this basename exists or get all
        attributes related to the file/dir.""",
        input_schema=FindFileNodeWithBasenameInput
    )

    find_file_node_with_relative_path_spec = ToolSpec(
        description="""Search FileNode in the graph with this relative_path of a file/dir. The relative_path is
        the relative path from the root path of codebase. The relative_path must include the extension,
        like 'foo/bar/baz.java'.

        You can use this tool to check if a file/dir with this relative_path exists or get all
        attributes related to the file/dir.""",
        input_schema=FindFileNodeWithRelativePathInput
    )

    # ASTNode retrieval tools
    find_ast_node_with_text_in_file_with_basename_spec = ToolSpec(
        description="""Find all ASTNode in the graph that exactly contains this text in any source file under 
        a file/directory with this basename. For reliable results, search for longer, distinct text 
        sequences rather than short common words or fragments. The contains is same as python's check 
        `'foo' in text`, ie. it is case sensitive and is looking for exact matches. For best results, 
        use unique text segments of at least several words. The basename can be either a file (like 
        'bar.py', 'baz.java') or a directory (like 'src' or 'test').""",
        input_schema=FindASTNodeWithTextInFileWithBasenameInput
    )

    find_ast_node_with_text_in_file_with_relative_path_spec = ToolSpec(
        description="""Find all ASTNode in the graph that exactly contains this text in any source file under 
        a file/directory with this relative path. For reliable results, search for longer, distinct text 
        sequences rather than short common words or fragments. The contains is same as python's check `'foo' in text`, 
        ie. it is case sensitive and is looking for exact matches. Therefore the search text should 
        be exact as well. The relative path should be the path from the root of codebase 
        (like 'src/core/parser.py' or 'test/unit').""",
        input_schema=FindASTNodeWithTextInFileWithRelativePathInput
    )

    find_ast_node_with_type_in_file_with_basename_spec = ToolSpec(
        description="""Find all ASTNode in the graph that has this tree-sitter node type in any source file under
        a file/directory with this basename. This tool is useful for searching class/function/method
        under a file/directory. The basename can be either a file (like 'bar.py', 
        'baz.java') or a directory (like 'core' or 'test').""",
        input_schema=FindASTNodeWithTypeInFileWithBasenameInput
    )

    find_ast_node_with_type_in_file_with_relative_path_spec = ToolSpec(
        description="""Find all ASTNode in the graph that has this tree-sitter node type in any source file under
        a file/directory with this relative path. This tool is useful for searching class/function/method
        under a file/directory. The relative path should be the path from the root 
        of codebase (like 'src/core/parser.py' or 'test/unit').""",
        input_schema=FindASTNodeWithTypeInFileWithRelativePathInput
    )

    # TextNode retrieval tools
    find_text_node_with_text_spec = ToolSpec(
        description="""Find all TextNode in the graph that exactly contains this text. The contains is
        same as python's check `'foo' in text`, ie. it is case sensitive and is
        looking for exact matches. Therefore the search text should be exact as well.

        You can use this tool to find all text/documentation in codebase that contains this text.""",
        input_schema=FindTextNodeWithTextInput
    )

    find_text_node_with_text_in_file_spec = ToolSpec(
        description="""Find all TextNode in the graph that exactly contains this text in a file with this basename.
        The contains is same as python's check `'foo' in text`, ie. it is case sensitive and is
        looking for exact matches. Therefore the search text should be exact as well.
        The basename must include the extension, like 'bar.py', 'baz.java' or 'foo'
        (in this case foo is a directory or a file without extension).

        You can use this tool to find text/documentation in a specific file that contains this text.""",
        input_schema=FindTextNodeWithTextInFileInput
    )

    get_next_text_node_with_node_id_spec = ToolSpec(
        description="""Get the next TextNode of this given node_id.

        You can use this tool to read the next section of text that you are interested in.""",
        input_schema=GetNextTextNodeWithNodeIdInput
    )

    # Other tools
    preview_file_content_with_basename_spec = ToolSpec(
        description="""Preview the content of a file with this basename. The basename must include
        the extension, like 'bar.py', 'baz.java' or 'foo' (in this case foo is a
        directory or a file without extension).

        You can use this tool to preview the content of a specific file to see what it contains
        in the first 1000 lines or the first section. If the file is interesting, use other tools
        to look at the file.""",
        input_schema=PreviewFileContentWithBasenameInput
    )

    preview_file_content_with_relative_path_spec = ToolSpec(
        description="""Preview the content of a file with this relative path from the root of codebase. 
        The relative path must include the extension and full path from root, like 'src/core/parser.py', 
        'test/unit/test_parser.java' or 'docs/README.md'.

        You can use this tool to preview the content of a specific file to see what it contains
        in the first 1000 lines or the first section. If the file is interesting, use other tools
        to look at the file.""",
        input_schema=PreviewFileContentWithRelativePathInput
    )

    read_code_with_basename_spec = ToolSpec(
        description="""Read a specific section of a source code file's content by specifying its basename and line range. 
        The basename must include the extension, like 'bar.py' or 'baz.java'

        This tool ONLY works with source code files (not text files or documentation). It is designed 
        to read large sections of code at once - you should request substantial chunks (hundreds of lines) 
        rather than making multiple small requests of 10-20 lines each, which would be inefficient.

        Line numbers are 1-indexed, where start_line is inclusive and end_line is exclusive. 

        This tool is useful for examining specific sections of source code files when you know 
        the exact line range you want to analyze. The function will return an error message if 
        end_line is less than start_line.""",
        input_schema=ReadCodeWithBasenameInput
    )

    read_code_with_relative_path_spec = ToolSpec(
        description="""Read a specific section of a source code file's content by specifying its relative path and line range. 
        The relative path must be the full path from the root of codebase, like 'src/core/parser.py' or 
        'test/unit/test_parser.java'.

        This tool ONLY works with source code files (not text files or documentation). It is designed 
        to read large sections of code at once - you should request substantial chunks (hundreds of lines) 
        rather than making multiple small requests of 10-20 lines each, which would be inefficient.

        Line numbers are 1-indexed, where start_line is inclusive and end_line is exclusive. 

        This tool is useful for examining specific sections of source code files when you know 
        the exact line range you want to analyze. The function will return an error message if 
        end_line is less than start_line.""",
        input_schema=ReadCodeWithRelativePathInput
    )

    def __init__(self, driver: GraphDatabase.driver, max_token_per_result: int):
        self.driver = driver
        self.max_token_per_result = max_token_per_result

    ###############################################################################
    #                          FileNode retrieval                                 #
    ###############################################################################

    def find_file_node_with_basename(self, basename: str) -> tuple[str, Sequence[Mapping[str, Any]]]:
        query = f"""
        MATCH (f:FileNode {{ basename: '{basename}' }})
        RETURN f AS FileNode
        ORDER BY f.node_id
        LIMIT {MAX_RESULT}
        """
        return neo4j_util.run_neo4j_query(query, self.driver, self.max_token_per_result)

    def find_file_node_with_relative_path(self, relative_path: str) -> tuple[str, Sequence[Mapping[str, Any]]]:
        query = f"""
        MATCH (f:FileNode {{ relative_path: '{relative_path}' }})
        RETURN f AS FileNode
        ORDER BY f.node_id
        LIMIT {MAX_RESULT}
        """
        return neo4j_util.run_neo4j_query(query, self.driver, self.max_token_per_result)

    ###############################################################################
    #                          ASTNode retrieval                                  #
    ###############################################################################

    def find_ast_node_with_text_in_file_with_basename(
        self, text: str, basename: str
    ) -> tuple[str, Sequence[Mapping[str, Any]]]:
        query = f"""\
        MATCH (f:FileNode) -[:HAS_FILE*0..]-> (c:FileNode) -[:HAS_AST]-> (:ASTNode) -[:PARENT_OF*0..]-> (a:ASTNode)
        WHERE f.basename = '{basename}' AND a.text CONTAINS '{text}'
        RETURN c as FileNode, a AS ASTNode
        ORDER BY SIZE(a.text)
        LIMIT {MAX_RESULT}
      """
        return neo4j_util.run_neo4j_query(query, self.driver, self.max_token_per_result)

    def find_ast_node_with_text_in_file_with_relative_path(
        self, text: str, relative_path: str
    ) -> tuple[str, Sequence[Mapping[str, Any]]]:
        query = f"""\
            MATCH (f:FileNode) -[:HAS_FILE*0..]-> (c:FileNode) -[:HAS_AST]-> (:ASTNode) -[:PARENT_OF*0..]-> (a:ASTNode)
            WHERE f.relative_path = '{relative_path}' AND a.text CONTAINS '{text}'
            RETURN c as FileNode, a AS ASTNode
            ORDER BY SIZE(a.text)
            LIMIT {MAX_RESULT}
        """
        return neo4j_util.run_neo4j_query(query, self.driver, self.max_token_per_result)

    def find_ast_node_with_type_in_file_with_basename(
        self, type: str, basename: str
    ) -> tuple[str, Sequence[Mapping[str, Any]]]:
        query = f"""\
        MATCH (f:FileNode) -[:HAS_FILE*0..]-> (c:FileNode) -[:HAS_AST]-> (:ASTNode) -[:PARENT_OF*0..]-> (a:ASTNode)
        WHERE f.basename = '{basename}' AND a.type = '{type}'
        RETURN c as FileNode, a AS ASTNode
        ORDER BY SIZE(a.text)
        LIMIT {MAX_RESULT}
      """
        return neo4j_util.run_neo4j_query(query, self.driver, self.max_token_per_result)

    def find_ast_node_with_type_in_file_with_relative_path(
        self, type: str, relative_path: str
    ) -> tuple[str, Sequence[Mapping[str, Any]]]:
        query = f"""\
            MATCH (f:FileNode) -[:HAS_FILE*0..]-> (c:FileNode) -[:HAS_AST]-> (:ASTNode) -[:PARENT_OF*0..]-> (a:ASTNode)
            WHERE f.relative_path = '{relative_path}' AND a.type = '{type}'
            RETURN c as FileNode, a AS ASTNode
            ORDER BY SIZE(a.text)
            LIMIT {MAX_RESULT}
        """
        return neo4j_util.run_neo4j_query(query, self.driver, self.max_token_per_result)

    ###############################################################################
    #                          TextNode retrieval                                 #
    ###############################################################################

    def find_text_node_with_text(
        self, text: str
    ) -> tuple[str, Sequence[Mapping[str, Any]]]:
        query = f"""\
        MATCH (f:FileNode) -[:HAS_TEXT]-> (t:TextNode)
        WHERE t.text CONTAINS '{text}'
        RETURN f as FileNode, t AS TextNode
        ORDER BY t.node_id
        LIMIT {MAX_RESULT}
      """
        return neo4j_util.run_neo4j_query(query, self.driver, self.max_token_per_result)

    def find_text_node_with_text_in_file(
        self, text: str, basename: str
    ) -> tuple[str, Sequence[Mapping[str, Any]]]:
        query = f"""\
        MATCH (f:FileNode) -[:HAS_TEXT]-> (t:TextNode)
        WHERE f.basename = '{basename}' AND t.text CONTAINS '{text}'
        RETURN f as FileNode, t AS TextNode
        ORDER BY t.node_id
        LIMIT {MAX_RESULT}
      """
        return neo4j_util.run_neo4j_query(query, self.driver, self.max_token_per_result)

    def get_next_text_node_with_node_id(
        self, node_id: int
    ) -> tuple[str, Sequence[Mapping[str, Any]]]:
        query = f"""\
        MATCH (f:FileNode) -[:HAS_TEXT]-> (a:TextNode {{ node_id: {node_id} }}) -[:NEXT_CHUNK]-> (b:TextNode)
        RETURN f as FileNode, b AS TextNode
      """
        return neo4j_util.run_neo4j_query(query, self.driver, self.max_token_per_result)

    ###############################################################################
    #                                 Other                                       #
    ###############################################################################

    def preview_file_content_with_basename(
        self, basename: str
    ) -> tuple[str, Sequence[Mapping[str, Any]]]:
        source_code_query = f"""\
        MATCH (f:FileNode {{ basename: '{basename}' }}) -[:HAS_AST]-> (a:ASTNode)
        WITH f, apoc.text.split(a.text, '\\R') AS lines
        RETURN
          f AS FileNode,
          {{
            text: apoc.text.join(lines[0..1000], '\\n'),
            start_line: 1,
            end_line: 1000
          }} AS preview
        ORDER BY f.node_id
      """

        text_query = f"""\
        MATCH (f:FileNode {{ basename: '{basename}' }}) -[:HAS_TEXT]-> (t:TextNode)
        WHERE NOT EXISTS((:TextNode) -[:NEXT_CHUNK]-> (t))
        RETURN f as FileNode, t.text AS preview
        ORDER BY f.node_id
      """

        if tree_sitter_parser.supports_file(Path(basename)):
            data = neo4j_util.run_neo4j_query_without_formatting(source_code_query, self.driver)
        else:
            data = neo4j_util.run_neo4j_query_without_formatting(text_query, self.driver)
        for result in data:
            if isinstance(result["preview"], dict):
                result["preview"]["text"] = pre_append_line_numbers(
                    result["preview"]["text"], result["preview"]["start_line"]
                )
                result["preview"]["end_line"] = (
                    result["preview"]["start_line"] + len(result["preview"]["text"].splitlines()) - 1
                )
        return neo4j_util.format_neo4j_data(data, self.max_token_per_result), data

    def preview_file_content_with_relative_path(
        self, relative_path: str
    ) -> tuple[str, Sequence[Mapping[str, Any]]]:
        source_code_query = f"""\
          MATCH (f:FileNode {{ relative_path: '{relative_path}' }}) -[:HAS_AST]-> (a:ASTNode)
          WITH f, apoc.text.split(a.text, '\\R') AS lines
          RETURN 
            f as FileNode,
            {{
              text: apoc.text.join(lines[0..1000], '\\n'),
              start_line: 1,
              end_line: 1000
            }} AS preview
          ORDER BY f.node_id
      """

        text_query = f"""\
          MATCH (f:FileNode {{ relative_path: '{relative_path}' }}) -[:HAS_TEXT]-> (t:TextNode)
          WHERE NOT EXISTS((:TextNode) -[:NEXT_CHUNK]-> (t))
          RETURN f as FileNode, t.text AS preview
          ORDER BY f.node_id
      """

        if tree_sitter_parser.supports_file(Path(relative_path)):
            data = neo4j_util.run_neo4j_query_without_formatting(source_code_query, self.driver)
        else:
            data = neo4j_util.run_neo4j_query_without_formatting(text_query, self.driver)
        for result in data:
            if isinstance(result["preview"], dict):
                result["preview"]["text"] = pre_append_line_numbers(
                    result["preview"]["text"], result["preview"]["start_line"]
                )
                result["preview"]["end_line"] = (
                    result["preview"]["start_line"] + len(result["preview"]["text"].splitlines()) - 1
                )
        return neo4j_util.format_neo4j_data(data, self.max_token_per_result), data

    def read_code_with_basename(
        self,
        basename: str,
        start_line: int,
        end_line: int,
    ) -> tuple[str, Union[Sequence[Mapping[str, Any]], None]]:
        if end_line < start_line:
            return f"end_line {end_line} must be greater than start_line {start_line}", None

        source_code_query = f"""\
        MATCH (f:FileNode {{ basename: '{basename}' }}) -[:HAS_AST]-> (a:ASTNode)
        WITH f, apoc.text.split(a.text, '\\R') AS lines
        RETURN
          f as FileNode,
          {{
            text: apoc.text.join(lines[{start_line - 1}..{end_line - 1}], '\\n'),
            start_line: {start_line},
            end_line: {end_line}
          }} AS SelectedLines
        ORDER BY f.node_id
      """
        data = neo4j_util.run_neo4j_query_without_formatting(source_code_query, self.driver)
        for result in data:
            result["SelectedLines"]["text"] = pre_append_line_numbers(
                result["SelectedLines"]["text"], result["SelectedLines"]["start_line"]
            )
        return neo4j_util.format_neo4j_data(data, self.max_token_per_result), data

    def read_code_with_relative_path(
        self,
        relative_path: str,
        start_line: int,
        end_line: int,
    ) -> tuple[str, Union[Sequence[Mapping[str, Any]], None]]:
        if end_line < start_line:
            return f"end_line {end_line} must be greater than start_line {start_line}", None

        source_code_query = f"""\
            MATCH (f:FileNode {{ relative_path: '{relative_path}' }}) -[:HAS_AST]-> (a:ASTNode)
            WITH f, apoc.text.split(a.text, '\\R') AS lines
            RETURN
              f as FileNode,
              {{
                text: apoc.text.join(lines[{start_line - 1}..{end_line - 1}], '\\n'),
                start_line: {start_line},
                end_line: {end_line}
              }} AS SelectedLines
            ORDER BY f.node_id
        """

        data = neo4j_util.run_neo4j_query_without_formatting(source_code_query, self.driver)
        for result in data:
            result["SelectedLines"]["text"] = pre_append_line_numbers(
                result["SelectedLines"]["text"], result["SelectedLines"]["start_line"]
            )

        return neo4j_util.format_neo4j_data(data, self.max_token_per_result), data

