# Technical Specification: Prime Number Calculator

## 1. Algorithm Selection

### Chosen Algorithm: Sieve of Eratosthenes

**Rationale:**
- **Efficiency**: O(n log log n) time complexity significantly outperforms trial division O(n√n) for generating primes up to n
- **Simplicity**: Straightforward to implement with minimal branching logic
- **Cache-friendly**: Sequential memory access pattern
- **Trade-off**: Higher memory usage is acceptable for the performance gain

**Alternative for single primality tests**: Trial division with 6k±1 optimization (used for `is_prime()` function on individual numbers)

---

## 2. API Definitions

### Module: `prime_calculator.py`

```python
from typing import List, Optional, Iterator

def is_prime(n: int) -> bool:
    """
    Check if a single number is prime.
    
    Args:
        n: Integer to test for primality
        
    Returns:
        bool: True if n is prime, False otherwise
        
    Algorithm: Trial division with 6k±1 optimization
    Time: O(√n)
    Space: O(1)
    """
    ...

def generate_primes(limit: int) -> List[int]:
    """
    Generate all prime numbers up to and including limit.
    
    Args:
        limit: Upper bound (inclusive) for prime generation
        
    Returns:
        List[int]: Sorted list of all primes <= limit
        
    Algorithm: Sieve of Eratosthenes
    Time: O(n log log n)
    Space: O(n)
    """
    ...

def prime_generator() -> Iterator[int]:
    """
    Infinite generator yielding primes in ascending order.
    
    Yields:
        int: Next prime number starting from 2
        
    Algorithm: Incremental sieve with trial division fallback
    Time: Amortized O(log n) per prime (approximate)
    Space: O(√n) for internal state
    """
    ...

def count_primes(limit: int) -> int:
    """
    Count primes up to and including limit without storing them.
    
    Args:
        limit: Upper bound (inclusive) for counting
        
    Returns:
        int: Count of primes <= limit
        
    Algorithm: Optimized Sieve of Eratosthenes (bit array)
    Time: O(n log log n)
    Space: O(n/8) - bit-packed boolean array
    """
    ...

def nth_prime(n: int) -> int:
    """
    Return the n-th prime (1-indexed: nth_prime(1) == 2).
    
    Args:
        n: Position in prime sequence (n >= 1)
        
    Returns:
        int: The n-th prime number
        
    Raises:
        ValueError: If n < 1
        
    Algorithm: Sieve with dynamic upper bound estimation
    Time: O(n log n) average
    Space: O(n log n)
    """
    ...
```

---

## 3. Complexity Analysis

| Function | Time Complexity | Space Complexity | Notes |
|----------|----------------|------------------|-------|
| `is_prime(n)` | O(√n) | O(1) | Best for single checks |
| `generate_primes(limit)` | O(n log log n) | O(n) | n = limit; boolean array |
| `prime_generator()` | O(log²n) amortized | O(√n) | Incremental generation |
| `count_primes(limit)` | O(n log log n) | O(n/8) | Bit array optimization |
| `nth_prime(n)` | O(n log n) avg | O(n log n) | Uses prime number theorem for bounds |

### Detailed Analysis

**Sieve of Erathenes (`generate_primes`):**
- Time: Each composite marked once per prime factor
- Space: Boolean array of size limit+1

**Trial Division (`is_prime`):**
- Checks divisibility up to √n
- 6k±1 optimization: only test 2, 3, then numbers of form 6k±1

---

## 4. Edge Cases

| Input | Expected Behavior | Implementation Note |
|-------|-------------------|---------------------|
| `n < 0` | Return `False` (not prime) | Negative numbers are not prime by definition |
| `n == 0` | Return `False` | Zero is not prime |
| `n == 1` | Return `False` | One is not prime (has only one factor) |
| `n == 2` | Return `True` | Smallest and only even prime |
| `n == 3` | Return `True` | Smallest odd prime |
| Even `n > 2` | Return `False` | All even numbers > 2 are composite |
| `limit < 2` | Return `[]` (empty list) | No primes below 2 |
| `limit == 2` | Return `[2]` | Single-element list |
| `nth_prime(0)` | Raise `ValueError` | Invalid input (n must be >= 1) |
| Very large `n` (> 2⁶³) | May overflow / slow | Document practical limit |

---

## 5. Implementation Notes

### Sieve Implementation Pattern
```python
def generate_primes(limit: int) -> List[int]:
    if limit < 2:
        return []
    
    sieve = [True] * (limit + 1)
    sieve[0] = sieve[1] = False
    
    for i in range(2, int(limit ** 0.5) + 1):
        if sieve[i]:
            for j in range(i * i, limit + 1, i):
                sieve[j] = False
    
    return [i for i, is_p in enumerate(sieve) if is_p]
```

### Trial Division Pattern (6k±1)
```python
def is_prime(n: int) -> bool:
    if n < 2:
        return False
    if n in (2, 3):
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False
    
    i = 5
    while i * i <= n:
        if n % i == 0 or n % (i + 2) == 0:
            return False
        i += 6
    return True
```

---

## 6. Testing Checklist

- [ ] `is_prime(-5)` → `False`
- [ ] `is_prime(0)` → `False`
- [ ] `is_prime(1)` → `False`
- [ ] `is_prime(2)` → `True`
- [ ] `is_prime(97)` → `True`
- [ ] `is_prime(100)` → `False`
- [ ] `generate_primes(10)` → `[2, 3, 5, 7]`
- [ ] `generate_primes(1)` → `[]`
- [ ] First 10 primes from generator → `[2, 3, 5, 7, 11, 13, 17, 19, 23, 29]`
- [ ] `count_primes(100)` → `25` (known value)
- [ ] `nth_prime(1)` → `2`
- [ ] `nth_prime(25)` → `97`
- [ ] `nth_prime(0)` raises `ValueError`

---

*Specification Version: 1.0*
*Author: Architect*
*Target Language: Python 3.9+*
