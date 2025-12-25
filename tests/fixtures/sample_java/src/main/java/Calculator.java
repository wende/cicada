/**
 * A simple calculator that performs basic arithmetic operations.
 *
 * This module provides basic arithmetic operations through the Calculator class.
 */
public class Calculator {
    /** The current value stored in the calculator. */
    private int value;

    /**
     * Initialize calculator with an optional starting value.
     *
     * @param initialValue The starting value (default: 0)
     */
    public Calculator(int initialValue) {
        this.value = initialValue;
    }

    /**
     * Default constructor with value 0.
     */
    public Calculator() {
        this(0);
    }

    /**
     * Add two numbers and return the result.
     *
     * @param x First number
     * @param y Second number
     * @return Sum of x and y
     */
    public int add(int x, int y) {
        return x + y;
    }

    /**
     * Multiply two numbers and return the result.
     *
     * @param x First number
     * @param y Second number
     * @return Product of x and y
     */
    public int multiply(int x, int y) {
        return x * y;
    }

    /**
     * Divide x by y and return the result.
     *
     * @param x Numerator
     * @param y Denominator
     * @return Result of division
     */
    public double divide(double x, double y) {
        return x / y;
    }

    /**
     * Private method (should be marked as private in index).
     */
    private String privateMethod() {
        return "private";
    }

    /**
     * Calculate a complex expression using multiple operations.
     *
     * @param x First operand
     * @param y Second operand
     * @param z Third operand
     * @return Result of (x + y) * z
     */
    public int calculateExpression(int x, int y, int z) {
        int sumResult = add(x, y);
        return multiply(sumResult, z);
    }

    /**
     * Top-level helper function to process data.
     *
     * @param data Array of items
     * @return Length of the array
     */
    public static int helperFunction(int[] data) {
        return data.length;
    }
}
