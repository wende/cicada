defmodule SampleStrings do
  @moduledoc """
  Test module for string extraction.
  This documentation should NOT be extracted as a string.
  """

  @doc """
  Function documentation should also be skipped.
  """
  def documented_function do
    "This string SHOULD be extracted"
  end

  def query_function do
    # SQL queries should be extracted
    "SELECT * FROM users WHERE active = true"
  end

  def error_messages do
    # Error messages should be extracted
    "User not found in the database"
    "Invalid credentials provided"
    "Connection timeout occurred"
  end

  def log_messages(user_id) do
    # Log messages should be extracted
    "Processing user request for ID: #{user_id}"
    "Request completed successfully"
  end

  def short_strings do
    # These short strings should be SKIPPED (< 3 chars)
    "a"
    "OK"
    ""
    "No"

    # This one should be extracted (>= 3 chars)
    "Yes"
  end

  def atom_like_strings do
    # These should ALL be extracted (no filtering for atom-like patterns)
    "Elixir.MyModule"
    ":ok"
    ":error"
    "ERROR"
    "SUCCESS"
    "Error message"
  end

  defp private_function do
    # Strings in private functions should also be extracted
    "This is from a private function"
  end

  def multiline_string do
    """
    This is a multiline string.
    It should be extracted as one string.
    It contains multiple lines.
    """
  end

  def interpolated_strings(name) do
    # Interpolated strings should be extracted
    "Hello, #{name}!"
    "Welcome to #{inspect(__MODULE__)}"
  end

  def config_values do
    # Configuration strings
    "database_connection_string"
    "api_endpoint_url"
    "authentication_token"
  end

  def ui_text do
    # User interface text
    "Click here to continue"
    "Please enter your email address"
    "Account created successfully"
  end

  def function_with_guard(x) when is_integer(x) do
    # Guards should not interfere with string extraction
    "Integer value received"
  end

  def nested_structures do
    # Strings in nested structures
    %{
      message: "This is a map value",
      error: "Something went wrong"
    }

    [
      "First item in list",
      "Second item in list"
    ]

    {"Tuple string one", "Tuple string two"}
  end

  @spec typed_function(String.t()) :: String.t()
  def typed_function(input) do
    # @spec should not interfere
    "Processing input string"
  end
end
