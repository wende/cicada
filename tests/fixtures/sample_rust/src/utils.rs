/// Utility functions for validation and formatting.
///
/// This module provides helper functions used across the application.

/// Validates an email address.
///
/// # Arguments
/// * `email` - The email address to validate
///
/// # Returns
/// true if the email contains '@' and is not empty, false otherwise
pub fn validate_email(email: &str) -> bool {
    !email.is_empty() && email.contains('@')
}

/// Formats a response message.
///
/// # Arguments
/// * `message` - The message to format
///
/// # Returns
/// A formatted string wrapped in brackets
pub fn format_response(message: String) -> String {
    format!("[RESPONSE] {}", message)
}

/// Sanitizes user input by trimming whitespace.
///
/// # Arguments
/// * `input` - The input string to sanitize
///
/// # Returns
/// A sanitized string with leading/trailing whitespace removed
pub fn sanitize_input(input: &str) -> String {
    input.trim().to_string()
}

/// Checks if a string is a valid identifier.
///
/// # Arguments
/// * `s` - The string to check
///
/// # Returns
/// true if the string contains only alphanumeric characters and underscores
pub fn is_valid_identifier(s: &str) -> bool {
    !s.is_empty() && s.chars().all(|c| c.is_alphanumeric() || c == '_')
}

/// Converts a string to title case.
///
/// # Arguments
/// * `s` - The string to convert
///
/// # Returns
/// A new string with the first character uppercase
pub fn to_title_case(s: &str) -> String {
    let mut chars = s.chars();
    match chars.next() {
        None => String::new(),
        Some(first) => first.to_uppercase().chain(chars).collect(),
    }
}

/// Private helper function for internal string processing.
fn _process_string(s: &str) -> String {
    s.to_lowercase()
}

/// Calculates the hash of a string (simplified).
///
/// # Arguments
/// * `s` - The string to hash
///
/// # Returns
/// A u64 hash value
pub fn simple_hash(s: &str) -> u64 {
    s.bytes().fold(0u64, |acc, b| acc.wrapping_mul(31).wrapping_add(b as u64))
}
