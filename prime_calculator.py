"""
Prime Number Calculator
----------------------
This module provides functionality to calculate prime numbers up to a 
specified limit or within a given range using the Sieve of Eratosthenes.
"""

import sys

def sieve_of_eratosthenes(limit):
    """
    Implements the Sieve of Eratosthenes to find all primes up to a given limit.
    
    Args:
        limit (int): The upper bound for finding prime numbers.
        
    Returns:
        list: A list of all prime numbers up to the limit.
    """
    if limit < 2:
        return []
    
    # Create a boolean array "prime[0..limit]" and initialize
    # all entries it as true. A value in prime[i] will
    # finally be false if i is Not a prime, else true.
    primes_mask = [True] * (limit + 1)
    primes_mask[0] = primes_mask[1] = False
    
    p = 2
    while (p * p <= limit):
        # If primes_mask[p] is not changed, then it is a prime
        if primes_mask[p]:
            # Update all multiples of p
            for i in range(p * p, limit + 1, p):
                primes_mask[i] = False
        p += 1
    
    # Return list of numbers where primes_mask is True
    return [p for p in range(2, limit + 1) if primes_mask[p]]

def get_primes_in_range(start, end):
    """
    Finds prime numbers within a specific range [start, end].
    
    Args:
        start (int): The start of the range.
        end (int): The end of the range.
        
    Returns:
        list: A list of prime numbers between start and end inclusive.
    """
    if start > end:
        return []
    
    # Use the sieve to get all primes up to 'end'
    all_primes = sieve_of_eratosthenes(end)
    
    # Filter the list for primes >= start
    return [p for p in all_primes if p >= start]

def main():
    """
    Main entry point for the prime calculator CLI.
    """
    print("--- Prime Number Calculator ---")
    print("Choose an option:")
    print("1. Find primes up to a limit")
    print("2. Find primes in a specific range")
    
    try:
        choice = input("Enter choice (1 or 2): ").strip()
        
        if choice == '1':
            limit = int(input("Enter the limit: "))
            primes = sieve_of_eratosthenes(limit)
            print(f"\nPrimes up to {limit}:")
            print(primes)
            print(f"Total count: {len(primes)}")
            
        elif choice == '2':
            start = int(input("Enter the start of the range: "))
            end = int(input("Enter the end of the range: "))
            primes = get_primes_in_range(start, end)
            print(f"\nPrimes between {start} and {end}:")
            print(primes)
            print(f"Total count: {len(primes)}")
            
        else:
            print("Invalid choice. Please select 1 or 2.")
            
    except ValueError:
        print("Error: Please enter valid integers.")
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)

if __name__ == "__main__":
    main()
