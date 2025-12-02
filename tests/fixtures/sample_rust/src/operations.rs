//! Basic arithmetic operations module.

/// Add two integers.
///
/// # Arguments
///
/// * `x` - First number
/// * `y` - Second number
///
/// # Returns
///
/// Sum of x and y
pub fn add(x: i32, y: i32) -> i32 {
    x + y
}

/// Multiply two integers.
///
/// # Arguments
///
/// * `x` - First number
/// * `y` - Second number
///
/// # Returns
///
/// Product of x and y
pub fn multiply(x: i32, y: i32) -> i32 {
    x * y
}

/// Divide two floating point numbers.
///
/// # Arguments
///
/// * `x` - Numerator
/// * `y` - Denominator
///
/// # Returns
///
/// Some(result) if y is not zero, None otherwise
pub fn divide(x: f64, y: f64) -> Option<f64> {
    if y == 0.0 {
        None
    } else {
        Some(x / y)
    }
}

/// Private helper function.
fn _internal_helper() -> i32 {
    42
}
