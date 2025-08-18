from prometheus.tools.file_operation import (
    create_file,
    delete,
    edit_file,
    read_file,
    read_file_with_line_numbers,
)
from tests.test_utils.fixtures import temp_test_dir  # noqa: F401


def test_create_and_read_file(temp_test_dir):  # noqa: F811
    """Test creating a file and reading its contents."""
    test_file = temp_test_dir / "test.txt"
    content = "line 1\nline 2\nline 3"

    # Test create_file
    result = create_file("test.txt", str(temp_test_dir), content)
    assert test_file.exists()
    assert test_file.read_text() == content
    assert result == "The file test.txt has been created."

    # Test read_file
    result = read_file("test.txt", str(temp_test_dir))
    expected = "1. line 1\n2. line 2\n3. line 3"
    assert result == expected


def test_read_file_nonexistent(temp_test_dir):  # noqa: F811
    """Test reading a nonexistent file."""
    result = read_file("nonexistent_file.txt", str(temp_test_dir))
    assert result == "The file nonexistent_file.txt does not exist."


def test_read_file_with_line_numbers(temp_test_dir):  # noqa: F811
    """Test reading specific line ranges from a file."""
    content = "line 1\nline 2\nline 3\nline 4\nline 5"
    create_file("test_lines.txt", str(temp_test_dir), content)

    # Test reading specific lines
    result = read_file_with_line_numbers("test_lines.txt", str(temp_test_dir), 2, 4)
    expected = "2. line 2\n3. line 3"
    assert result == expected

    # Test invalid range
    result = read_file_with_line_numbers("test_lines.txt", str(temp_test_dir), 4, 2)
    assert result == "The end line number 2 must be greater than the start line number 4."


def test_delete(temp_test_dir):  # noqa: F811
    """Test file and directory deletion."""
    # Test file deletion
    test_file = temp_test_dir / "to_delete.txt"
    create_file("to_delete.txt", str(temp_test_dir), "content")
    assert test_file.exists()
    result = delete("to_delete.txt", str(temp_test_dir))
    assert result == "The file to_delete.txt has been deleted."
    assert not test_file.exists()

    # Test directory deletion
    test_subdir = temp_test_dir / "subdir"
    test_subdir.mkdir()
    create_file("subdir/file.txt", str(temp_test_dir), "content")
    result = delete("subdir", str(temp_test_dir))
    assert result == "The directory subdir has been deleted."
    assert not test_subdir.exists()


def test_delete_nonexistent(temp_test_dir):  # noqa: F811
    """Test deleting a nonexistent path."""
    result = delete("nonexistent_path", str(temp_test_dir))
    assert result == "The file nonexistent_path does not exist."


def test_edit_file(temp_test_dir):  # noqa: F811
    """Test editing specific lines in a file."""
    # Test case 1: Successfully edit a single occurrence
    initial_content = "line 1\nline 2\nline 3\nline 4\nline 5"
    create_file("edit_test.txt", str(temp_test_dir), initial_content)
    result = edit_file("edit_test.txt", str(temp_test_dir), "line 2", "new line 2")
    assert result == "Successfully edited edit_test.txt."

    # Test case 2: Absolute path error
    result = edit_file("/edit_test.txt", str(temp_test_dir), "line 2", "new line 2")
    assert result == "relative_path: /edit_test.txt is a absolute path, not relative path."

    # Test case 3: File doesn't exist
    result = edit_file("nonexistent.txt", str(temp_test_dir), "line 2", "new line 2")
    assert result == "The file nonexistent.txt does not exist."

    # Test case 4: No matches found
    result = edit_file("edit_test.txt", str(temp_test_dir), "nonexistent line", "new content")
    assert (
        result
        == "No match found for the specified content in edit_test.txt. Please verify the content to replace."
    )

    # Test case 5: Multiple occurrences
    duplicate_content = "line 1\nline 2\nline 2\nline 3"
    create_file("duplicate_test.txt", str(temp_test_dir), duplicate_content)
    result = edit_file("duplicate_test.txt", str(temp_test_dir), "line 2", "new line 2")
    assert (
        result
        == "Found 2 occurrences of the specified content in duplicate_test.txt. Please provide more context to ensure a unique match."
    )


def test_create_file_already_exists(temp_test_dir):  # noqa: F811
    """Test creating a file that already exists."""
    create_file("existing.txt", str(temp_test_dir), "content")
    result = create_file("existing.txt", str(temp_test_dir), "new content")
    assert result == "The file existing.txt already exists."
