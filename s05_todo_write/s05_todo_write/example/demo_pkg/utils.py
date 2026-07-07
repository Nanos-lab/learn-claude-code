"""Utility functions for the demo package."""

from typing import Any, List


def add(a: float, b: float) -> float:
    """Return the sum of two numbers.

    Args:
        a: First number.
        b: Second number.

    Returns:
        The sum a + b.

    Examples:
        >>> add(2, 3)
        5
        >>> add(-1, 1)
        0
    """
    return a + b


def capitalize_words(text: str) -> str:
    """Capitalize the first letter of each word in a string.

    Args:
        text: The input string.

    Returns:
        The string with each word capitalized.

    Examples:
        >>> capitalize_words("hello world")
        'Hello World'
        >>> capitalize_words("python package demo")
        'Python Package Demo'
    """
    return " ".join(word.capitalize() for word in text.split())


def is_palindrome(text: str) -> bool:
    """Check if a string is a palindrome (case-insensitive).

    Args:
        text: The input string.

    Returns:
        True if the string is a palindrome, False otherwise.

    Examples:
        >>> is_palindrome("racecar")
        True
        >>> is_palindrome("Hello")
        False
        >>> is_palindrome("A man a plan a canal Panama")
        False
    """
    cleaned = text.lower()
    return cleaned == cleaned[::-1]


def flatten(nested: List[Any]) -> List[Any]:
    """Flatten a list of lists into a single flat list.

    Args:
        nested: A list potentially containing sub-lists.

    Returns:
        A new flat list with all elements.

    Examples:
        >>> flatten([[1, 2], [3, 4], [5]])
        [1, 2, 3, 4, 5]
        >>> flatten([])
        []
    """
    result: List[Any] = []
    for item in nested:
        if isinstance(item, list):
            result.extend(flatten(item))
        else:
            result.append(item)
    return result


def chunk(items: List[Any], size: int) -> List[List[Any]]:
    """Split a list into chunks of the given size.

    Args:
        items: The list to split.
        size: The maximum size of each chunk.

    Returns:
        A list of chunks.

    Raises:
        ValueError: If size is less than 1.

    Examples:
        >>> chunk([1, 2, 3, 4, 5], 2)
        [[1, 2], [3, 4], [5]]
        >>> chunk([1, 2, 3], 1)
        [[1], [2], [3]]
    """
    if size < 1:
        raise ValueError("Chunk size must be at least 1.")
    return [items[i:i + size] for i in range(0, len(items), size)]
