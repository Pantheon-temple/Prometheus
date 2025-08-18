"""
Tree-sitter-based code parsing module.

This module provides functionality to parse source code files using tree-sitter,
supporting multiple programming languages. It handles file type detection and
parsing operations, returning a syntax tree representation of the source code.

The module uses tree-sitter parsers from the tree_sitter_languages package
and supports various common programming languages including Python, Java,
JavaScript, C++, Rust, Ruby, TypeScript and others.
"""

from pathlib import Path

from tree_sitter._binding import Tree
from tree_sitter_languages import get_parser

from prometheus.parser.file_types import FileType


class FileNotSupportedError(Exception):
    """Exception raised when attempting to parse an unsupported file type.

    This exception is raised when the parser encounters a file type
    not supported by the tree-sitter parser implementation.
    """

    pass


FILE_TYPE_TO_LANG = {
    # Supported programming languages
    FileType.BASH: "bash",
    FileType.C: "c",
    FileType.CSHARP: "c_sharp",
    FileType.CPP: "cpp",
    FileType.GO: "go",
    FileType.JAVA: "java",
    FileType.JAVASCRIPT: "javascript",
    FileType.KOTLIN: "kotlin",
    FileType.PHP: "php",
    FileType.PYTHON: "python",
    FileType.SQL: "sql",
    FileType.RUST: "rust",
    FileType.RUBY: "ruby",
    FileType.TYPESCRIPT: "typescript",
    # Configuration files
    FileType.YAML: "yaml",
}


def supports_file(file: Path) -> bool:
    """Checks if the parser supports a given file type.

    Args:
      file: A Path object representing the file to check.

    Returns:
      bool: True if the file type is supported, False otherwise.
    """
    file_type = FileType.from_path(file)
    return file_type in FILE_TYPE_TO_LANG


def parse(file: Path) -> Tree:
    """Parses a source code file using the appropriate tree-sitter parser.

    Args:
      file: A Path object representing the file to parse.

    Returns:
      Tree: A tree-sitter Tree object representing the parsed syntax tree.

    Raises:
      FileNotSupportedError: If the parser does not support the file type.
    """
    file_type = FileType.from_path(file)
    lang = FILE_TYPE_TO_LANG.get(file_type, None)
    if lang is None:
        raise FileNotSupportedError(f"{file_type.value} is not supported by tree_sitter_parser")

    lang_parser = get_parser(lang)
    with file.open("rb") as f:
        return lang_parser.parse(f.read())
