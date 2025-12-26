/**
 * Main entry point for the calculator module.
 */

const { Calculator } = require('./calculator');
const { formatNumber, sum, average } = require('./utils');

/**
 * Create and use a calculator.
 * @returns {object} Results object
 */
function runCalculations() {
  const calc = new Calculator(10);
  calc.add(5);
  calc.multiply(2);
  return {
    value: calc.getValue(),
    formatted: formatNumber(calc.getValue())
  };
}

/**
 * Process a list of numbers.
 * @param {number[]} numbers - Input numbers
 * @returns {object} Statistics
 */
function processNumbers(numbers) {
  return {
    sum: sum(numbers),
    average: average(numbers),
    count: numbers.length
  };
}

module.exports = { runCalculations, processNumbers, Calculator };
