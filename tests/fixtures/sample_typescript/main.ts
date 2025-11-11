/**
 * Main entry point for calculator application.
 *
 * Demonstrates usage of all modules and cross-file dependencies.
 */

import { Calculator } from "./calculator";
import { add, subtract, multiply } from "./operations";
import { chainAdd, average } from "./utils";

/**
 * Run sample calculations using all modules.
 */
export function runCalculations(): void {
  // Create calculator instance
  const calc = new Calculator(10);

  // Multiple calls to the same function (operations.add via calc.add)
  const result1 = calc.add(5, 3); // First call to calc.add
  const result2 = calc.add(10, 20); // Second call to calc.add
  const result3 = calc.add(result1, result2); // Third call to calc.add

  // Direct calls to operations module
  const sumVal = add(100, 200); // Call operations.add directly
  const diff = subtract(sumVal, 50);
  const product = multiply(diff, 2);

  // Use utils module
  const numbers = [1, 2, 3, 4, 5];
  const total = chainAdd(numbers); // Call utils.chainAdd
  const avg = average(numbers); // Call utils.average

  // Multiple calls to calc methods
  calc.multiply(5, 6);
  calc.multiply(3, 4);
  calc.divide(100, 4);

  // Format results
  const formatted = calc.formatValue(avg);

  console.log(`Results: ${result3}, ${product}, ${total}, ${formatted}`);
}

/**
 * Process input data and return results.
 *
 * @param data - Input data array
 * @returns Object with processed results
 */
export function processData(data: number[]): {
  total: number;
  average: number;
  count: number;
} {
  if (data.length === 0) {
    return { total: 0, average: 0, count: 0 };
  }

  const total = chainAdd(data); // Another call to chainAdd
  const avgVal = average(data); // Another call to average

  return {
    total: total,
    average: avgVal,
    count: data.length,
  };
}

/**
 * Private helper function (not exported).
 */
function _internalMainHelper(x: number, y: number): number {
  return add(x, y); // Call operations.add from private function
}

// Main execution
if (require.main === module) {
  runCalculations();
  const sampleData = [10, 20, 30, 40, 50];
  const results = processData(sampleData);
  console.log(`Data processing results:`, results);
}
