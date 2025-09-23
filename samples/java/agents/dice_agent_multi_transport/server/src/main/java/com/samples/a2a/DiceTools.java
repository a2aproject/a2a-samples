package com.samples.a2a;

import dev.langchain4j.agent.tool.Tool;
import jakarta.enterprise.context.ApplicationScoped;
import java.util.HashSet;
import java.util.List;
import java.util.Random;
import java.util.Set;

/** Service class that provides dice rolling and prime number functionality. */
@ApplicationScoped
public class DiceTools {

  /** For generating rolls. */
  private final Random random = new Random();

  /** Default number of sides to use. */
  private static final int DEFAULT_NUM_SIDES = 6;

  /**
   * Rolls an N sided dice. If number of sides aren't given, uses 6.
   *
   * @param n the number of the side of the dice to roll
   * @return A number between 1 and N, inclusive
   */
  @Tool("Rolls an n sided dice. If number of sides aren't given, uses 6.")
  public int rollDice(final int n) {
    int sides = n;
    if (sides <= 0) {
      sides = DEFAULT_NUM_SIDES; // Default to 6 sides if invalid input
    }
    return random.nextInt(sides) + 1;
  }

  /**
   * Check if a given list of numbers are prime.
   *
   * @param nums The list of numbers to check
   * @return A string indicating which number is prime
   */
  @Tool("Check if a given list of numbers are prime.")
  public String checkPrime(final List<Integer> nums) {
    Set<Integer> primes = new HashSet<>();

    for (Integer number : nums) {
      if (number == null) {
        continue;
      }

      int num = number.intValue();
      if (num <= 1) {
        continue;
      }

      boolean isPrime = true;
      for (int i = 2; i <= Math.sqrt(num); i++) {
        if (num % i == 0) {
          isPrime = false;
          break;
        }
      }

      if (isPrime) {
        primes.add(num);
      }
    }

    if (primes.isEmpty()) {
      return "No prime numbers found.";
    } else {
      return primes.stream()
              .sorted()
              .map(String::valueOf)
              .collect(java.util.stream.Collectors.joining(", "))
          + " are prime numbers.";
    }
  }
}
