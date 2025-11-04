/// Configuration management for the application.
///
/// This module handles application configuration and settings.

use serde::{Deserialize, Serialize};

/// Application configuration.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Config {
    /// Server host address
    pub host: String,
    /// Server port number
    pub port: u16,
    /// Maximum number of connections
    pub max_connections: usize,
    /// Whether debug mode is enabled
    pub debug: bool,
}

impl Config {
    /// Creates a new Config with default values.
    ///
    /// # Returns
    /// A new Config instance with sensible defaults
    pub fn new() -> Self {
        Self {
            host: String::from("localhost"),
            port: 8080,
            max_connections: 100,
            debug: false,
        }
    }

    /// Creates a Config for production use.
    ///
    /// # Returns
    /// A Config instance optimized for production
    pub fn production() -> Self {
        Self {
            host: String::from("0.0.0.0"),
            port: 80,
            max_connections: 1000,
            debug: false,
        }
    }

    /// Creates a Config for development use.
    ///
    /// # Returns
    /// A Config instance optimized for development
    pub fn development() -> Self {
        Self {
            host: String::from("127.0.0.1"),
            port: 3000,
            max_connections: 10,
            debug: true,
        }
    }

    /// Updates the host address.
    ///
    /// # Arguments
    /// * `host` - The new host address
    pub fn set_host(&mut self, host: String) {
        self.host = host;
    }

    /// Updates the port number.
    ///
    /// # Arguments
    /// * `port` - The new port number
    pub fn set_port(&mut self, port: u16) {
        self.port = port;
    }

    /// Enables debug mode.
    pub fn enable_debug(&mut self) {
        self.debug = true;
    }

    /// Disables debug mode.
    pub fn disable_debug(&mut self) {
        self.debug = false;
    }

    /// Gets the full server address.
    ///
    /// # Returns
    /// A string in the format "host:port"
    pub fn server_address(&self) -> String {
        format!("{}:{}", self.host, self.port)
    }

    /// Validates the configuration.
    ///
    /// # Returns
    /// true if the configuration is valid, false otherwise
    pub fn is_valid(&self) -> bool {
        !self.host.is_empty() && self.port > 0 && self.max_connections > 0
    }

    /// Private method to check if running in secure mode.
    fn _is_secure(&self) -> bool {
        self.port == 443
    }
}

impl Default for Config {
    fn default() -> Self {
        Self::new()
    }
}

/// Helper function to load configuration from environment.
///
/// # Returns
/// A Config instance based on environment variables
pub fn load_from_env() -> Config {
    // Simplified implementation for demonstration
    Config::new()
}

/// Private helper for config validation.
fn _validate_port(port: u16) -> bool {
    port > 1024
}
