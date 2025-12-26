/**
 * A simple calculator class.
 */
class Calculator {
  /**
   * Create a calculator with initial value.
   * @param {number} initialValue - Starting value
   */
  constructor(initialValue = 0) {
    this.value = initialValue;
  }

  /**
   * Add a number to the current value.
   * @param {number} x - Number to add
   * @returns {number} New value
   */
  add(x) {
    this.value += x;
    return this.value;
  }

  /**
   * Multiply the current value.
   * @param {number} x - Multiplier
   * @returns {number} New value
   */
  multiply(x) {
    this.value *= x;
    return this.value;
  }

  /**
   * Get the current value.
   * @returns {number} Current value
   */
  getValue() {
    return this.value;
  }

  /**
   * Reset the calculator.
   */
  reset() {
    this.value = 0;
  }
}

module.exports = { Calculator };
