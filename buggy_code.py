"""
A buggy Python file to test the Gemini Swarm Debugger
"""

def calculate_average(numbers):
    """Calculate the average of a list of numbers."""
    # Bug 1: Missing check for empty list
    return sum(numbers) / len(numbers)

def find_max_value(numbers):
    """Find the maximum value in a list."""
    # Bug 2: Missing check for empty list
    max_val = numbers[0]
    for num in numbers:
        if num > max_val:
            max_val = num
    return max_val

def filter_positive_numbers(numbers):
    """Filter only positive numbers from a list."""
    # Bug 3: Logic error with filter condition
    positive_numbers = []
    for num in numbers:
        if num >= 0:  # Should be > 0 for strictly positive
            positive_numbers.append(num)
    return positive_numbers

def count_words_in_string(text):
    """Count the number of words in a string."""
    # Bug 4: Doesn't handle multiple spaces correctly
    return len(text.split())

def reverse_string(text):
    """Reverse a string."""
    # Bug 5: Doesn't handle None input
    return text[::-1]

def main():
    """Test function to run calculations."""
    numbers = [1, 2, 3, 4, 5]
    print(f"Average: {calculate_average(numbers)}")
    print(f"Max value: {find_max_value(numbers)}")
    print(f"Positive numbers: {filter_positive_numbers([-2, -1, 0, 1, 2])}")
    print(f"Word count: {count_words_in_string('The quick brown fox')}")
    print(f"Reversed string: {reverse_string('hello')}")

if __name__ == "__main__":
    main()