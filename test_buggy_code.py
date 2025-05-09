"""
Test file for buggy_code.py to validate fixes
"""
import unittest
from buggy_code import (
    calculate_average,
    find_max_value,
    filter_positive_numbers,
    count_words_in_string,
    reverse_string
)

class TestBuggyCode(unittest.TestCase):
    """Test cases for the buggy code functions."""
    
    def test_calculate_average(self):
        """Test the calculate_average function."""
        self.assertEqual(calculate_average([1, 2, 3, 4, 5]), 3.0)
        self.assertEqual(calculate_average([10]), 10.0)
        # Should handle empty list
        with self.assertRaises(ValueError):
            calculate_average([])
    
    def test_find_max_value(self):
        """Test the find_max_value function."""
        self.assertEqual(find_max_value([1, 2, 3, 4, 5]), 5)
        self.assertEqual(find_max_value([5, 4, 3, 2, 1]), 5)
        self.assertEqual(find_max_value([-5, -10, -1]), -1)
        self.assertEqual(find_max_value([10]), 10)
        # Should handle empty list
        with self.assertRaises(ValueError):
            find_max_value([])
    
    def test_filter_positive_numbers(self):
        """Test the filter_positive_numbers function."""
        # Should only include strictly positive numbers (> 0)
        self.assertEqual(filter_positive_numbers([-2, -1, 0, 1, 2]), [1, 2])
        self.assertEqual(filter_positive_numbers([1, 2, 3]), [1, 2, 3])
        self.assertEqual(filter_positive_numbers([-1, -2, -3]), [])
        self.assertEqual(filter_positive_numbers([0]), [])
        self.assertEqual(filter_positive_numbers([]), [])
    
    def test_count_words_in_string(self):
        """Test the count_words_in_string function."""
        self.assertEqual(count_words_in_string("The quick brown fox"), 4)
        self.assertEqual(count_words_in_string("Hello,  world!"), 2)  # Multiple spaces
        self.assertEqual(count_words_in_string(""), 0)
        self.assertEqual(count_words_in_string("   "), 0)  # Only spaces
    
    def test_reverse_string(self):
        """Test the reverse_string function."""
        self.assertEqual(reverse_string("hello"), "olleh")
        self.assertEqual(reverse_string(""), "")
        # Should handle None without error
        self.assertIsNone(reverse_string(None))

if __name__ == "__main__":
    unittest.main()