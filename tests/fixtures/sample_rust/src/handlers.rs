/// Request handlers for user and task operations.
///
/// This module contains handler structs that process requests
/// and interact with the data models.

use crate::models::{User, Task};
use crate::utils::{validate_email, format_response};

/// Handles user-related operations.
pub struct UserHandler {
    users: Vec<User>,
}

impl UserHandler {
    /// Creates a new UserHandler.
    ///
    /// # Returns
    /// A new UserHandler with an empty user list
    pub fn new() -> Self {
        Self { users: Vec::new() }
    }

    /// Adds a new user to the system.
    ///
    /// # Arguments
    /// * `user` - The user to add
    ///
    /// # Returns
    /// true if the user was added successfully, false if email is invalid
    pub fn add_user(&mut self, user: User) -> bool {
        if !validate_email(&user.email) {
            return false;
        }
        self.users.push(user);
        true
    }

    /// Finds a user by ID.
    ///
    /// # Arguments
    /// * `id` - The user ID to search for
    ///
    /// # Returns
    /// A reference to the user if found, None otherwise
    pub fn find_user(&self, id: u64) -> Option<&User> {
        self.users.iter().find(|u| u.id == id)
    }

    /// Updates a user's information.
    ///
    /// # Arguments
    /// * `id` - The user ID to update
    /// * `new_name` - The new name to set
    ///
    /// # Returns
    /// true if the user was found and updated, false otherwise
    pub fn update_user(&mut self, id: u64, new_name: String) -> bool {
        if let Some(user) = self.users.iter_mut().find(|u| u.id == id) {
            user.update_name(new_name);
            true
        } else {
            false
        }
    }

    /// Deletes a user by ID.
    ///
    /// # Arguments
    /// * `id` - The user ID to delete
    ///
    /// # Returns
    /// true if the user was deleted, false if not found
    pub fn delete_user(&mut self, id: u64) -> bool {
        let original_len = self.users.len();
        self.users.retain(|u| u.id != id);
        self.users.len() < original_len
    }

    /// Lists all active users.
    ///
    /// # Returns
    /// A vector of references to all active users
    pub fn list_active_users(&self) -> Vec<&User> {
        self.users.iter().filter(|u| u.is_active).collect()
    }

    /// Gets the total number of users.
    ///
    /// # Returns
    /// The count of all users in the system
    pub fn count(&self) -> usize {
        self.users.len()
    }

    /// Private method to validate user data.
    fn _validate_user_data(&self, user: &User) -> bool {
        !user.email.is_empty() && !user.name.is_empty()
    }
}

impl Default for UserHandler {
    fn default() -> Self {
        Self::new()
    }
}

/// Handles task-related operations.
pub struct TaskHandler {
    tasks: Vec<Task>,
}

impl TaskHandler {
    /// Creates a new TaskHandler.
    ///
    /// # Returns
    /// A new TaskHandler with an empty task list
    pub fn new() -> Self {
        Self { tasks: Vec::new() }
    }

    /// Adds a new task to the system.
    ///
    /// # Arguments
    /// * `task` - The task to add
    pub fn add_task(&mut self, task: Task) {
        self.tasks.push(task);
    }

    /// Finds a task by ID.
    ///
    /// # Arguments
    /// * `id` - The task ID to search for
    ///
    /// # Returns
    /// A reference to the task if found, None otherwise
    pub fn find_task(&self, id: u64) -> Option<&Task> {
        self.tasks.iter().find(|t| t.id == id)
    }

    /// Assigns a task to a user.
    ///
    /// # Arguments
    /// * `task_id` - The ID of the task to assign
    /// * `user_id` - The ID of the user to assign to
    ///
    /// # Returns
    /// true if the task was found and assigned, false otherwise
    pub fn assign_task(&mut self, task_id: u64, user_id: u64) -> bool {
        if let Some(task) = self.tasks.iter_mut().find(|t| t.id == task_id) {
            task.assign_to(user_id);
            true
        } else {
            false
        }
    }

    /// Marks a task as completed.
    ///
    /// # Arguments
    /// * `task_id` - The ID of the task to complete
    ///
    /// # Returns
    /// true if the task was found and completed, false otherwise
    pub fn complete_task(&mut self, task_id: u64) -> bool {
        if let Some(task) = self.tasks.iter_mut().find(|t| t.id == task_id) {
            task.complete();
            true
        } else {
            false
        }
    }

    /// Lists all incomplete tasks.
    ///
    /// # Returns
    /// A vector of references to all incomplete tasks
    pub fn list_incomplete_tasks(&self) -> Vec<&Task> {
        self.tasks.iter().filter(|t| !t.completed).collect()
    }

    /// Generates a summary report of all tasks.
    ///
    /// # Returns
    /// A formatted string with task summaries
    pub fn generate_report(&self) -> String {
        let summaries: Vec<String> = self.tasks.iter().map(|t| t.summary()).collect();
        format_response(summaries.join("\n"))
    }

    /// Gets the count of completed tasks.
    ///
    /// # Returns
    /// Number of completed tasks
    pub fn count_completed(&self) -> usize {
        self.tasks.iter().filter(|t| t.completed).count()
    }
}

impl Default for TaskHandler {
    fn default() -> Self {
        Self::new()
    }
}

/// Top-level helper function to process multiple handlers.
///
/// # Arguments
/// * `user_handler` - Reference to a UserHandler
/// * `task_handler` - Reference to a TaskHandler
///
/// # Returns
/// A summary string of users and tasks
pub fn generate_system_summary(user_handler: &UserHandler, task_handler: &TaskHandler) -> String {
    format!(
        "Users: {}, Tasks: {}",
        user_handler.count(),
        task_handler.count_completed()
    )
}
