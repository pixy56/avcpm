"""Tests for prime_calculator.py"""

import pytest
from prime_calculator import calculate_primes


class TestCalculatePrimes:
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

    def test_limit_0(self):
        assert calculate_primes(0) == []

    def test_limit_2(self):
        assert calculate_primes(2) == [2]

    def test_negative_limit_raises_error(self):
        with pytest.raises(ValueError, match="non-negative"):
            calculate_primes(-5)