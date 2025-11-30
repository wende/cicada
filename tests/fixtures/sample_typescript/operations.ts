/**
 * Basic arithmetic operations module.
 *
 * Provides fundamental math operations with type safety.
 */

/**
 * Add two numbers together.
 *
 * @param x - First number
 * @param y - Second number
 * @returns Sum of x and y
 */
export function add(x: number, y: number): number {
  return x + y;
}

/**
 * Subtract y from x.
 *
 * @param x - Number to subtract from
 * @param y - Number to subtract
 * @returns Difference of x and y
 */
export function subtract(x: number, y: number): number {
  return x - y;
}

/**
 * Multiply two numbers.
 *
 * @param x - First number
 * @param y - Second number
 * @returns Product of x and y
 */
export function multiply(x: number, y: number): number {
  return x * y;
}

/**
 * Divide x by y with error handling.
 *
 * @param x - Numerator
 * @param y - Denominator
 * @returns Result of division
 * @throws Error if y is zero
 */
export function divide(x: number, y: number): number {
  if (y === 0) {
    throw new Error("Cannot divide by zero");
  }
  return x / y;
}

/**
 * Private internal operation (not exported).
 */
function _internalOperation(value: number): number {
  return Math.abs(value);
}
