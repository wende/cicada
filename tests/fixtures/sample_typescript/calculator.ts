/**
 * A simple calculator that performs basic arithmetic operations.
 */
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
   * Add two numbers.
   *
   * @param x - First number
   * @param y - Second number
   * @returns Sum of x and y
   */
  add(x: number, y: number): number {
    return x + y;
  }

  /**
   * Multiply two numbers.
   *
   * @param x - First number
   * @param y - Second number
   * @returns Product of x and y
   */
  multiply(x: number, y: number): number {
    return x * y;
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
