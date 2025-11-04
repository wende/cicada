/**
 * Utility functions for calculator operations.
 *
 * Helper functions that build on basic operations.
 */

import * as operations from "./operations";

/** Constant for testing imports */
export const MAX_PRECISION = 10;

/**
 * Add a list of numbers by chaining add operations.
 *
 * @param numbers - Array of numbers to add
 * @returns Sum of all numbers
 */
export function chainAdd(numbers: number[]): number {
  if (numbers.length === 0) {
    return 0;
  }

  let result = numbers[0];
  for (let i = 1; i < numbers.length; i++) {
    result = operations.add(result, numbers[i]); // Cross-file call
  }
  return result;
}

/**
 * Calculate average of numbers using operations module.
 *
 * @param numbers - Array of numbers
 * @returns Average value
 * @throws Error if array is empty
 */
export function average(numbers: number[]): number {
  if (numbers.length === 0) {
    throw new Error("Cannot average empty array");
  }

  const total = chainAdd(numbers); // Internal call
  return operations.divide(total, numbers.length); // Cross-file call
}

/**
 * Format a numeric result as a string.
 *
 * @param value - Number to format
 * @param precision - Decimal places (default: 2)
 * @returns Formatted string
 */
export function formatResult(value: number, precision: number = 2): string {
  if (precision > MAX_PRECISION) {
    precision = MAX_PRECISION;
  }
  return value.toFixed(precision);
}

/**
 * Private helper that uses operations (not exported).
 */
function _internalHelper(x: number, y: number): number {
  const temp = operations.multiply(x, 2); // Cross-file call from private function
  return operations.add(temp, y);
}
