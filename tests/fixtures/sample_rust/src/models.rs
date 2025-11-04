/// Data models for the application.
///
/// This module defines the core data structures used throughout the system.

use serde::{Deserialize, Serialize};

/// Represents a user in the system.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct User {
    /// Unique identifier for the user
    pub id: u64,
    /// User's email address
    pub email: String,
    /// User's display name
    pub name: String,
    /// Whether the user account is active
    pub is_active: bool,
}

impl User {
    /// Creates a new user with the given details.
    ///
    /// # Arguments
    /// * `id` - Unique user identifier
    /// * `email` - User's email address
    /// * `name` - User's display name
    ///
    /// # Returns
    /// A new User instance with is_active set to true
    pub fn new(id: u64, email: String, name: String) -> Self {
        Self {
            id,
            email,
            name,
            is_active: true,
        }
    }

    /// Activates the user account.
    pub fn activate(&mut self) {
        self.is_active = true;
    }

    /// Deactivates the user account.
    pub fn deactivate(&mut self) {
        self.is_active = false;
    }

    /// Checks if the user's email is valid.
    ///
    /// # Returns
    /// true if the email contains '@', false otherwise
    pub fn has_valid_email(&self) -> bool {
        crate::utils::validate_email(&self.email)
    }

    /// Updates the user's name.
    ///
    /// # Arguments
    /// * `new_name` - The new name to set
    pub fn update_name(&mut self, new_name: String) {
        self.name = new_name;
    }

    /// Private helper to check if user has admin privileges.
    ///
    /// This is a demonstration of a private method.
    fn _is_admin(&self) -> bool {
        self.email.ends_with("@admin.com")
    }
}

/// Represents a task that can be assigned to users.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Task {
    /// Unique identifier for the task
    pub id: u64,
    /// Task title
    pub title: String,
    /// Detailed task description
    pub description: String,
    /// ID of the user assigned to this task
    pub assigned_to: Option<u64>,
    /// Whether the task is completed
    pub completed: bool,
}

impl Task {
    /// Creates a new task.
    ///
    /// # Arguments
    /// * `id` - Unique task identifier
    /// * `title` - Task title
    /// * `description` - Detailed description
    ///
    /// # Returns
    /// A new Task instance with completed set to false
    pub fn new(id: u64, title: String, description: String) -> Self {
        Self {
            id,
            title,
            description,
            assigned_to: None,
            completed: false,
        }
    }

    /// Assigns the task to a user.
    ///
    /// # Arguments
    /// * `user_id` - The ID of the user to assign
    pub fn assign_to(&mut self, user_id: u64) {
        self.assigned_to = Some(user_id);
    }

    /// Marks the task as completed.
    pub fn complete(&mut self) {
        self.completed = true;
    }

    /// Checks if the task is assigned to anyone.
    ///
    /// # Returns
    /// true if the task has an assigned user, false otherwise
    pub fn is_assigned(&self) -> bool {
        self.assigned_to.is_some()
    }

    /// Gets the formatted task summary.
    ///
    /// # Returns
    /// A string containing the task title and status
    pub fn summary(&self) -> String {
        let status = if self.completed { "✓" } else { "○" };
        format!("{} {} - {}", status, self.id, self.title)
    }
}

/// Private helper function for internal use.
fn _internal_helper() -> bool {
    true
}

/// Top-level function to count active tasks.
///
/// # Arguments
/// * `tasks` - Slice of tasks to count
///
/// # Returns
/// Number of tasks that are not completed
pub fn count_active_tasks(tasks: &[Task]) -> usize {
    tasks.iter().filter(|t| !t.completed).count()
}
