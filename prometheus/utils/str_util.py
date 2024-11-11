def pre_append_line_numbers(text: str, start_line: int) -> str:
    """
    Prepends line numbers to each line of the given text, starting from a specified line number.

    This utility function takes a multi-line text and adds line numbers to the beginning of each line,
    starting from the specified start line number. It is useful for displaying text with line numbering,
    such as in code snippets, log outputs, or file contents.

    Args:
        text (str): The input text to be numbered. Can be a single line or multiple lines.
        start_line (int): The line number to start numbering from. Typically a positive integer.

    Returns:
        str: The input text with line numbers prepended to each line, separated by '. '.

    Example:
        >>> pre_append_line_numbers("Hello\nWorld", 10)
        '10. Hello\n11. World'
        >>> pre_append_line_numbers("Single line", 5)
        '5. Single line'
    """
    return "\n".join([f"{start_line + i}. {line}" for i, line in enumerate(text.splitlines())])
