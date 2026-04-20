# Prime Number Calculator

A high-performance Python library for calculating prime numbers using the Sieve of Eratosthenes algorithm.

## Features

- **Efficient Algorithm**: Uses the Sieve of Eratosthenes (O(n log log n) time complexity)
- **Range Queries**: Find primes within specific ranges
- **Type Hints**: Fully typed for better IDE support
- **Well Tested**: Comprehensive test suite included

## Installation

### Requirements

- Python 3.9 or higher

### Setup

Clone the repository and install dependencies:

```bash
git clone <repository-url>
cd prime-calculator
pip install -r requirements.txt  # if dependencies exist
```

For development, install pytest:

```bash
pip install pytest
```

## Usage

### Basic Usage

```python
from primes import calculate_primes

# Get all primes up to 100
primes = calculate_primes(100)
print(primes)
# Output: [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97]

# Count the primes
print(f"Found {len(primes)} primes")
# Output: Found 25 primes
```

### CLI Mode

Run the interactive CLI:

```bash
python prime_calculator.py
```

This presents a menu with options to:
1. Find primes up to a limit
2. Find primes within a specific range

Example session:
```
--- Prime Number Calculator ---
Choose an option:
1. Find primes up to a limit
2. Find primes in a specific range
Enter choice (1 or 2): 1
Enter the limit: 50

Primes up to 50:
[2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47]
Total count: 15
```

### Range Queries

```python
from prime_calculator import get_primes_in_range

# Find primes between 10 and 50
primes = get_primes_in_range(10, 50)
print(primes)
# Output: [11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47]
```

## API Documentation

### `calculate_primes(limit: int) -> List[int]`

Returns a list of all prime numbers up to and including the given limit.

**Parameters:**
- `limit` (int): The upper bound (inclusive) for finding primes. Values below 2 return an empty list.

**Returns:**
- `List[int]`: A sorted list of prime integers from 2 up to `limit`.

**Time Complexity:** O(n log log n) where n = limit  
**Space Complexity:** O(n)

**Example:**
```python
from primes import calculate_primes

# Empty list for limits < 2
calculate_primes(1)   # Returns: []

# Single prime
calculate_primes(2)   # Returns: [2]

# Multiple primes
calculate_primes(10)  # Returns: [2, 3, 5, 7]
```

---

### `sieve_of_eratosthenes(limit: int) -> List[int]`

Alias for `calculate_primes`. Implements the Sieve of Eratosthenes algorithm.

**Parameters:**
- `limit` (int): The upper bound for finding prime numbers.

**Returns:**
- `List[int]`: A list of all prime numbers up to the limit.

---

### `get_primes_in_range(start: int, end: int) -> List[int]`

Finds prime numbers within a specific range [start, end] inclusive.

**Parameters:**
- `start` (int): The start of the range.
- `end` (int): The end of the range.

**Returns:**
- `List[int]`: A list of prime numbers between start and end inclusive.

**Edge Cases:**
- Returns empty list if `start > end`
- Returns empty list if `end < 2`

**Example:**
```python
from prime_calculator import get_primes_in_range

get_primes_in_range(10, 20)   # Returns: [11, 13, 17, 19]
get_primes_in_range(20, 10)   # Returns: [] (invalid range)
get_primes_in_range(0, 1)     # Returns: [] (no primes < 2)
```

## Algorithm Details

### Sieve of Eratosthenes

The implementation uses the classic Sieve of Eratosthenes algorithm:

1. Create a boolean array of size `limit + 1`, initialized to `True`
2. Mark 0 and 1 as non-prime (`False`)
3. For each number `i` from 2 to √limit:
   - If `i` is prime (still marked `True`), mark all multiples of `i` as non-prime
   - Start marking from `i * i` (all smaller multiples already marked)
4. Collect all indices that remain `True` as primes

**Optimizations:**
- Only iterate up to √limit for marking
- Start marking multiples from `i * i`
- Single-pass boolean array for cache efficiency

## Testing

Run the test suite with pytest:

```bash
pytest test_prime_calculator.py -v
```

### Test Coverage

The test suite covers:

- **Edge Cases:** Limits less than 2 return empty lists
- **Basic Functionality:** First few prime numbers
- **Known Values:** All 25 primes up to 100
- **Error Handling:** Negative input handling

### Example Tests

```python
def test_limit_less_than_2_returns_empty_list(self):
    assert calculate_primes(-1) == []
    assert calculate_primes(0) == []
    assert calculate_primes(1) == []

def test_first_primes(self):
    assert calculate_primes(2) == [2]
    assert calculate_primes(3) == [2, 3]
    assert calculate_primes(10) == [2, 3, 5, 7]

def test_primes_up_to_100(self):
    expected = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 
               53, 59, 61, 67, 71, 73, 79, 83, 89, 97]
    assert calculate_primes(100) == expected
```

## Project Structure

```
.
├── prime_calculator.py        # Main module with CLI and range queries
├── primes.py                  # Core prime calculation (calculate_primes)
├── test_prime_calculator.py   # Test suite
├── prime_calculator_spec.md    # Technical specification
└── README.md                   # This file
```

## Performance Notes

| Operation | Time Complexity | Space Complexity |
|-----------|----------------|------------------|
| `calculate_primes(n)` | O(n log log n) | O(n) |
| `get_primes_in_range(a, b)` | O(b log log b) | O(b) |

The Sieve of Eratosthenes is significantly faster than trial division for generating all primes up to a limit. For single primality tests on very large numbers, trial division or probabilistic methods may be more appropriate.

## License

This project is provided as-is for educational and development purposes.

## Contributing

Contributions welcome! Please ensure:
1. Code follows the existing style
2. Tests pass (`pytest`)
3. New features include appropriate tests
4. Documentation is updated accordingly
