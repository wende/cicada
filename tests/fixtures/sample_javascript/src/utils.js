/**
 * Utility functions for the calculator.
 */

/**
 * Format a number with fixed decimal places.
 * @param {number} value - The value to format
 * @param {number} decimals - Number of decimal places
 * @returns {string} Formatted string
 */
function formatNumber(value, decimals = 2) {
  return value.toFixed(decimals);
}

/**
 * Sum an array of numbers.
 * @param {number[]} numbers - Array of numbers
 * @returns {number} Sum of all numbers
 */
function sum(numbers) {
  return numbers.reduce((acc, n) => acc + n, 0);
}

/**
 * Calculate average of numbers.
 * @param {number[]} numbers - Array of numbers
 * @returns {number} Average value
 */
function average(numbers) {
  if (numbers.length === 0) return 0;
  return sum(numbers) / numbers.length;
}

/**
 * Private helper function.
 */
function _privateHelper() {
  return "internal";
}

module.exports = { formatNumber, sum, average };
