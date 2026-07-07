"""Tests for demo_pkg.utils."""

import pytest

from demo_pkg.utils import add, capitalize_words, is_palindrome, flatten, chunk


class TestAdd:
    """Tests for the add function."""

    def test_positive_numbers(self):
        assert add(2, 3) == 5

    def test_negative_numbers(self):
        assert add(-2, -3) == -5

    def test_mixed_signs(self):
        assert add(-1, 1) == 0

    def test_floats(self):
        assert add(2.5, 3.1) == pytest.approx(5.6)


class TestCapitalizeWords:
    """Tests for the capitalize_words function."""

    def test_simple(self):
        assert capitalize_words("hello world") == "Hello World"

    def test_single_word(self):
        assert capitalize_words("python") == "Python"

    def test_multiple_spaces(self):
        assert capitalize_words("a  b") == "A" + " " + "B"

    def test_empty_string(self):
        assert capitalize_words("") == ""


class TestIsPalindrome:
    """Tests for the is_palindrome function."""

    def test_simple_palindrome(self):
        assert is_palindrome("racecar") is True

    def test_not_palindrome(self):
        assert is_palindrome("hello") is False

    def test_case_insensitive(self):
        assert is_palindrome("RaceCar") is True

    def test_single_character(self):
        assert is_palindrome("a") is True

    def test_empty_string(self):
        assert is_palindrome("") is True


class TestFlatten:
    """Tests for the flatten function."""

    def test_flat_list(self):
        assert flatten([1, 2, 3]) == [1, 2, 3]

    def test_nested_lists(self):
        assert flatten([[1, 2], [3, 4], [5]]) == [1, 2, 3, 4, 5]

    def test_deeply_nested(self):
        assert flatten([[1, [2, 3]], [4]]) == [1, 2, 3, 4]

    def test_empty_list(self):
        assert flatten([]) == []


class TestChunk:
    """Tests for the chunk function."""

    def test_even_split(self):
        assert chunk([1, 2, 3, 4], 2) == [[1, 2], [3, 4]]

    def test_uneven_split(self):
        assert chunk([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]

    def test_size_one(self):
        assert chunk([1, 2, 3], 1) == [[1], [2], [3]]

    def test_size_larger_than_list(self):
        assert chunk([1, 2], 10) == [[1, 2]]

    def test_invalid_size(self):
        with pytest.raises(ValueError, match="Chunk size must be at least 1"):
            chunk([1, 2], 0)
