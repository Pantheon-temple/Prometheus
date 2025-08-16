import os
import shutil
from pathlib import Path
from dataclasses import dataclass
from pydantic import BaseModel, Field

from prometheus.utils.str_util import pre_append_line_numbers
from prometheus.utils.logger_manager import get_logger

logger = get_logger(__name__)

@dataclass
class ToolSpec:
    description: str
    input_schema: type

class ReadFileInput(BaseModel):
    relative_path: str = Field("The relative path of the file to read")

class ReadFileWithLineNumbersInput(BaseModel):
    relative_path: str = Field(
        description="The relative path of the file to read, eg. foo/bar/test.py, not absolute path"
    )
    start_line: int = Field(description="The start line number to read, 1-indexed and inclusive")
    end_line: int = Field(description="The ending line number to read, 1-indexed and exclusive")

class CreateFileInput(BaseModel):
    relative_path: str = Field(
        description="The relative path of the file to create, eg. foo/bar/test.py, not absolute path"
    )
    content: str = Field(description="The content of the file to create")

class DeleteInput(BaseModel):
    relative_path: str = Field(
        description="The relative path of the file/dir to delete, eg. foo/bar/test.py, not absolute path"
    )

class EditFileInput(BaseModel):
    relative_path: str = Field(
        description="The relative path of the file to edit, eg. foo/bar/test.py, not absolute path"
    )
    old_content: str = Field(
        description="The exact string content to be replaced in the file. Must match exactly one occurrence in the file"
    )
    new_content: str = Field(
        description="The new content that will replace the old_content in the file"
    )


class FileOperationTool:
    """Tool class for file operations including reading, creating, editing, and deleting files."""
    
    # File operation tools
    read_file_spec = ToolSpec(
        description="""\
        Read the content of a file with line numbers prepended from the codebase with a safety limit on the number of lines.
        Returns up to the first 1000 lines by default to prevent context issues with large files.
        Returns an error message if the file doesn't exist.
        """,
        input_schema=ReadFileInput
    )
    
    read_file_with_line_numbers_spec = ToolSpec(
        description="""\
        Read a specific range of lines from a file and return the content with line numbers prepended.
        The line numbers are 1-indexed where start_line is inclusive and end_line is exclusive.
        For best results when analyzing code or text files, consider reading chunks of 500-1000 lines at a time.
        """,
        input_schema=ReadFileWithLineNumbersInput
    )
    
    create_file_spec = ToolSpec(
        description="""\
        Create a new file at the specified path with the given content. 
        If the parent directories don't exist, they will be created automatically.
        Returns an error message if the file already exists.
        """,
        input_schema=CreateFileInput
    )
    
    delete_spec = ToolSpec(
        description="""\
        Delete a file or directory at the specified path.
        For directories, it will recursively delete all contents.
        Returns an error message if the path doesn't exist.
        """,
        input_schema=DeleteInput
    )
    
    edit_file_spec = ToolSpec(
        description="""\
        Edit a file by replacing specific content with new content.
        Performs an exact string replacement of old_content with new_content.
        Returns an error message if:
        - The file doesn't exist
        - The old_content is not found in the file
        - The old_content matches multiple locations (in which case more context is needed)
        - The provided path is absolute instead of relative

        Example usage:
        edit_file(
            relative_path="src/calculator.py",
            old_content="return a * b",
            new_content="return a / b"
        )
        """,
        input_schema=EditFileInput
    )
    
    def __init__(self, root_path: str):
        """Initialize the file operation tool.
        
        Args:
            root_path: The root path of the codebase for relative path operations.
        """
        self.root_path = root_path
    
    def read_file(self, relative_path: str, n_lines: int = 1000) -> str:
        if os.path.isabs(relative_path):
            return f"relative_path: {relative_path} is a abolsute path, not relative path."

        file_path = Path(os.path.join(self.root_path, relative_path))
        if not file_path.exists():
            return f"The file {relative_path} does not exist."

        with file_path.open() as f:
            lines = f.readlines()

        return pre_append_line_numbers("".join(lines[:n_lines]), 1)
    
    def read_file_with_line_numbers(self, relative_path: str, start_line: int, end_line: int) -> str:
        if os.path.isabs(relative_path):
            return f"relative_path: {relative_path} is a abolsute path, not relative path."

        file_path = Path(os.path.join(self.root_path, relative_path))
        if not file_path.exists():
            return f"The file {relative_path} does not exist."

        if end_line < start_line:
            return f"The end line number {end_line} must be greater than the start line number {start_line}."

        zero_based_start_line = start_line - 1
        zero_based_end_line = end_line - 1

        with file_path.open() as f:
            lines = f.readlines()

        return pre_append_line_numbers(
            "".join(lines[zero_based_start_line:zero_based_end_line]), start_line
        )
    
    def create_file(self, relative_path: str, content: str) -> str:
        if os.path.isabs(relative_path):
            return f"relative_path: {relative_path} is a abolsute path, not relative path."

        file_path = Path(os.path.join(self.root_path, relative_path))
        if file_path.exists():
            return f"The file {relative_path} already exists."

        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)
        return f"The file {relative_path} has been created."

    
    def delete(self, relative_path: str) -> str:
        if os.path.isabs(relative_path):
            return f"relative_path: {relative_path} is a abolsute path, not relative path."

        file_path = Path(os.path.join(self.root_path, relative_path))
        if not file_path.exists():
            return f"The file {relative_path} does not exist."

        if file_path.is_dir():
            shutil.rmtree(file_path)
            return f"The directory {relative_path} has been deleted."

        file_path.unlink()
        return f"The file {relative_path} has been deleted."
    
    def edit_file(self, relative_path: str, old_content: str, new_content: str) -> str:
        if os.path.isabs(relative_path):
            return f"relative_path: {relative_path} is a abolsute path, not relative path."

        file_path = Path(os.path.join(self.root_path, relative_path))
        if not file_path.exists():
            return f"The file {relative_path} does not exist."

        content = file_path.read_text()

        occurrences = content.count(old_content)

        if occurrences == 0:
            return f"No match found for the specified content in {relative_path}. Please verify the content to replace."

        if occurrences > 1:
            return (
                f"Found {occurrences} occurrences of the specified content in {relative_path}. "
                "Please provide more context to ensure a unique match."
            )

        new_content_full = content.replace(old_content, new_content)
        file_path.write_text(new_content_full)

        return f"Successfully edited {relative_path}."


READ_FILE_DESCRIPTION = """\
Read the content of a file with line numbers prepended from the codebase with a safety limit on the number of lines.
Returns up to the first 1000 lines by default to prevent context issues with large files.
Returns an error message if the file doesn't exist.
"""


def read_file(relative_path: str, root_path: str, n_lines: int = 1000) -> str:
    if os.path.isabs(relative_path):
        return f"relative_path: {relative_path} is a abolsute path, not relative path."

    file_path = Path(os.path.join(root_path, relative_path))
    if not file_path.exists():
        return f"The file {relative_path} does not exist."

    with file_path.open() as f:
        lines = f.readlines()

    return pre_append_line_numbers("".join(lines[:n_lines]), 1)




READ_FILE_WITH_LINE_NUMBERS_DESCRIPTION = """\
Read a specific range of lines from a file and return the content with line numbers prepended.
The line numbers are 1-indexed where start_line is inclusive and end_line is exclusive.
For best results when analyzing code or text files, consider reading chunks of 500-1000 lines at a time.
"""


def read_file_with_line_numbers(
    relative_path: str, root_path: str, start_line: int, end_line: int
) -> str:
    if os.path.isabs(relative_path):
        return f"relative_path: {relative_path} is a abolsute path, not relative path."

    file_path = Path(os.path.join(root_path, relative_path))
    if not file_path.exists():
        return f"The file {relative_path} does not exist."

    if end_line < start_line:
        return f"The end line number {end_line} must be greater than the start line number {start_line}."

    zero_based_start_line = start_line - 1
    zero_based_end_line = end_line - 1

    with file_path.open() as f:
        lines = f.readlines()

    return pre_append_line_numbers(
        "".join(lines[zero_based_start_line:zero_based_end_line]), start_line
    )



CREATE_FILE_DESCRIPTION = """\
Create a new file at the specified path with the given content. 
If the parent directories don't exist, they will be created automatically.
Returns an error message if the file already exists.
"""


def create_file(relative_path: str, root_path: str, content: str) -> str:
    if os.path.isabs(relative_path):
        return f"relative_path: {relative_path} is a abolsute path, not relative path."

    file_path = Path(os.path.join(root_path, relative_path))
    if file_path.exists():
        return f"The file {relative_path} already exists."

    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content)
    return f"The file {relative_path} has been created."



DELETE_DESCRIPTION = """\
Delete a file or directory at the specified path.
For directories, it will recursively delete all contents.
Returns an error message if the path doesn't exist.
"""


def delete(relative_path: str, root_path: str) -> str:
    if os.path.isabs(relative_path):
        return f"relative_path: {relative_path} is a abolsute path, not relative path."

    file_path = Path(os.path.join(root_path, relative_path))
    if not file_path.exists():
        return f"The file {relative_path} does not exist."

    if file_path.is_dir():
        shutil.rmtree(file_path)
        return f"The directory {relative_path} has been deleted."

    file_path.unlink()
    return f"The file {relative_path} has been deleted."



EDIT_FILE_DESCRIPTION = """\
Edit a file by replacing specific content with new content.
Performs an exact string replacement of old_content with new_content.
Returns an error message if:
- The file doesn't exist
- The old_content is not found in the file
- The old_content matches multiple locations (in which case more context is needed)
- The provided path is absolute instead of relative

Example usage:
edit_file(
    relative_path="src/calculator.py",
    old_content="return a * b",
    new_content="return a / b"
)
"""


def edit_file(relative_path: str, root_path: str, old_content: str, new_content: str) -> str:
    if os.path.isabs(relative_path):
        return f"relative_path: {relative_path} is a abolsute path, not relative path."

    file_path = Path(os.path.join(root_path, relative_path))
    if not file_path.exists():
        return f"The file {relative_path} does not exist."

    content = file_path.read_text()

    occurrences = content.count(old_content)

    if occurrences == 0:
        return f"No match found for the specified content in {relative_path}. Please verify the content to replace."

    if occurrences > 1:
        return (
            f"Found {occurrences} occurrences of the specified content in {relative_path}. "
            "Please provide more context to ensure a unique match."
        )

    new_content_full = content.replace(old_content, new_content)
    file_path.write_text(new_content_full)

    return f"Successfully edited {relative_path}."
