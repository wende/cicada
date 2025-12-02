//! Sample Rust library for testing Cicada SCIP indexing.
//!
//! This module provides basic arithmetic operations through the Calculator struct.

pub mod operations;
pub mod utils;

/// A simple calculator that performs basic arithmetic operations.
pub struct Calculator {
    /// The current value stored in the calculator.
    pub value: i32,
}

impl Calculator {
    /// Create a new calculator with an optional starting value.
    ///
    /// # Arguments
    ///
    /// * `initial_value` - The starting value (default: 0)
    pub fn new(initial_value: i32) -> Self {
        Calculator { value: initial_value }
    }

    /// Add two numbers using operations module.
    ///
    /// # Arguments
    ///
    /// * `x` - First number
    /// * `y` - Second number
    ///
    /// # Returns
    ///
    /// Sum of x and y
    pub fn add(&self, x: i32, y: i32) -> i32 {
        operations::add(x, y)
    }

    /// Multiply two numbers using operations module.
    ///
    /// # Arguments
    ///
    /// * `x` - First number
    /// * `y` - Second number
    ///
    /// # Returns
    ///
    /// Product of x and y
    pub fn multiply(&self, x: i32, y: i32) -> i32 {
        operations::multiply(x, y)
    }

    /// Divide x by y.
    ///
    /// # Arguments
    ///
    /// * `x` - Numerator
    /// * `y` - Denominator
    ///
    /// # Returns
    ///
    /// Result of division, or None if y is zero
    pub fn divide(&self, x: f64, y: f64) -> Option<f64> {
        operations::divide(x, y)
    }

    /// Private method (should be marked as private in index).
    fn _private_method(&self) -> &str {
        "private"
    }

    /// Calculate a complex expression using multiple operations.
    ///
    /// # Arguments
    ///
    /// * `x` - First operand
    /// * `y` - Second operand
    /// * `z` - Third operand
    ///
    /// # Returns
    ///
    /// Result of (x + y) * z
    pub fn calculate_expression(&self, x: i32, y: i32, z: i32) -> i32 {
        let sum_result = self.add(x, y);
        self.multiply(sum_result, z)
    }
}

/// A trait for displayable results.
pub trait Displayable {
    /// Format the value as a string.
    fn format(&self) -> String;
}

impl Displayable for Calculator {
    fn format(&self) -> String {
        format!("Calculator(value={})", self.value)
    }
}

/// Top-level function to process data.
///
/// # Arguments
///
/// * `data` - Slice of items
///
/// # Returns
///
/// Length of the slice
pub fn helper_function(data: &[i32]) -> usize {
    data.len()
}

/// Private function (no pub keyword).
fn _private_function() {
    // Private implementation
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_calculator_add() {
        let calc = Calculator::new(0);
        assert_eq!(calc.add(2, 3), 5);
    }
}
