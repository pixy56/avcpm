"""Calculate prime numbers using the Sieve of Eratosthenes."""

from typing import List


def calculate_primes(limit: int) -> List[int]:
    """Return a list of all primes <= limit.

    Args:
        limit: Upper bound (inclusive). Values below 2 return an empty list.

    Returns:
        A sorted list of prime integers from 2 up to *limit*.
    """
    if limit < 2:
        return []

    sieve = [True] * (limit + 1)
    sieve[0] = sieve[1] = False

    for i in range(2, int(limit**0.5) + 1):
        if sieve[i]:
            for multiple in range(i * i, limit + 1, i):
                sieve[multiple] = False

    return [n for n, is_prime in enumerate(sieve) if is_prime]


if __name__ == "__main__":
    primes = calculate_primes(100)
    print(f"Primes up to 100 ({len(primes)} found):")
    print(primes)
