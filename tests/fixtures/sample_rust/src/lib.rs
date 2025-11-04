/// Sample Rust library for testing SCIP indexing.
///
/// This library provides a simple user management and task tracking system
/// to demonstrate various Rust language features for cicada indexing.

pub mod models;
pub mod handlers;
pub mod utils;
pub mod config;

pub use models::{User, Task};
pub use handlers::{UserHandler, TaskHandler};
pub use utils::{validate_email, format_response};
pub use config::Config;
