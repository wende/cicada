/**
 * A simple calculator that performs basic arithmetic operations.
 */

import * as operations from "./operations";
import { chainAdd, formatResult } from "./utils";

export class Calculator {
  private value: number;

  /**
   * Initialize calculator with an optional starting value.
   *
   * @param initialValue - The starting value (default: 0)
   */
  constructor(initialValue: number = 0) {
    this.value = initialValue;
  }

  /**
   * Add two numbers using operations module.
   *
   * @param x - First number
   * @param y - Second number
   * @returns Sum of x and y
   */
  add(x: number, y: number): number {
    return operations.add(x, y); // Cross-file call
  }

  /**
   * Multiply two numbers using operations module.
   *
   * @param x - First number
   * @param y - Second number
   * @returns Product of x and y
   */
  multiply(x: number, y: number): number {
    return operations.multiply(x, y); // Cross-file call
  }

  /**
   * Divide x by y.
   *
   * @param x - Numerator
   * @param y - Denominator
   * @returns Result of division
   */
  divide(x: number, y: number): number {
    return operations.divide(x, y); // Cross-file call
  }

  /**
   * Sum a list of numbers using utils module.
   *
   * @param numbers - Array of numbers
   * @returns Sum of all numbers
   */
  sumList(numbers: number[]): number {
    return chainAdd(numbers); // Cross-file call to utils
  }

  /**
   * Format a value using utils module.
   *
   * @param value - Number to format
   * @returns Formatted string
   */
  formatValue(value: number): string {
    return formatResult(value); // Cross-file call to utils
  }

  /**
   * Private method (should be marked as private in index).
   */
  private _privateMethod(): string {
    return "private";
  }
}

/**
 * Top-level function to process data.
 *
 * @param data - Array of items
 * @returns Length of the array
 */
export function helperFunction(data: any[]): number {
  return data.length;
}

/**
 * Private function (not exported).
 */
function _privateFunction(): void {
  console.log("private");
}
