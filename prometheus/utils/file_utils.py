import os
from pathlib import Path

from prometheus.exceptions.file_operation_exceptions import FileOperationException


def read_file_with_line_numbers(
    relative_path: str, root_path: str, start_line: int, end_line: int
) -> str:
    if os.path.isabs(relative_path):
        raise FileOperationException(
            f"relative_path: {relative_path} is a absolute path, not relative path."
        )

    file_path = Path(os.path.join(root_path, relative_path))
    if not file_path.exists():
        raise FileOperationException(f"The file {relative_path} does not exist.")

    if not file_path.is_file():
        raise FileOperationException(f"The path {relative_path} is not a file.")

    if end_line < start_line:
        raise FileOperationException(
            f"The end line number {end_line} must be greater than "
            f"the start line number {start_line}."
        )

    zero_based_start_line = start_line - 1
    # The content in the end line is included
    zero_based_end_line = end_line

    with file_path.open() as f:
        lines = f.readlines()

    return "".join(lines[zero_based_start_line:zero_based_end_line])
