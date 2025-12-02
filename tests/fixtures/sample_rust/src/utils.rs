//! Utility functions for the calculator.

/// Chain add a list of numbers.
///
/// # Arguments
///
/// * `numbers` - Slice of numbers to add
///
/// # Returns
///
/// Sum of all numbers
pub fn chain_add(numbers: &[i32]) -> i32 {
    numbers.iter().sum()
}

/// Format a result as a string.
///
/// # Arguments
///
/// * `value` - Value to format
///
/// # Returns
///
/// Formatted string representation
pub fn format_result(value: i32) -> String {
    format!("Result: {}", value)
}

/// An enum representing operation types.
pub enum OperationType {
    Add,
    Subtract,
    Multiply,
    Divide,
}

impl OperationType {
    /// Get the symbol for this operation.
    pub fn symbol(&self) -> &str {
        match self {
            OperationType::Add => "+",
            OperationType::Subtract => "-",
            OperationType::Multiply => "*",
            OperationType::Divide => "/",
        }
    }
}
