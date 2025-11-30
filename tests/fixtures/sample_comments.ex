defmodule SampleComments do
  @moduledoc """
  Test module for comment extraction.
  This documentation should NOT be extracted as a comment.
  """

  # This is a top-level comment before any functions
  # It should be associated with the first function

  @doc """
  Function with a comment before it.
  """
  # This comment is right before the function definition
  # It should be associated with this function
  def function_with_comment_before do
    :ok
  end

  def function_with_inline_comments do
    # This is an inline comment inside the function
    x = 1 + 2

    # This comment explains the next operation
    y = x * 3

    # Return the result
    {:ok, y}
  end

  # TODO: Implement proper validation
  # FIXME: This is a known issue
  def function_with_markers do
    # BUG: Edge case not handled
    :error
  end

  def function_with_consecutive_comments do
    # Step 1: Validate input
    # Step 2: Process data
    # Step 3: Return result
    validate_input()

    # This is a separate comment block
    # after some code
    process_data()

    :ok
  end

  def function_with_blank_line_comments do
    # First block line 1
    # First block line 2

    # Second block line 1
    # Second block line 2
    :ok
  end

  def function_with_trailing_comment do
    do_work()
    # Trailing comment for previous function
  end

  def function_with_leading_comment do
    # Leading comment for next function
    :ready
  end

  # Short comments: #a #b #c should be filtered out
  def function_with_short_comments do
    # ok
    # no
    # This comment is long enough to be extracted
    :result
  end

  defp private_function_with_comments do
    # Private functions can have comments too
    # This should be extracted normally
    "private result"
  end

  def function_with_nested_structures do
    # Comment before conditional
    if true do
      # Inside if block
      :yes
    else
      # Inside else block
      :no
    end

    # Comment before case
    case :value do
      :value ->
        # Inside case clause
        :matched
      _ ->
        # Default case
        :default
    end
  end

  def function_with_pipeline do
    # Comment before pipeline
    :input
    |> process_step_one()
    # Comment in middle of pipeline (rare but possible)
    |> process_step_two()
    |> process_step_three()
  end

  def no_comments_function do
    :clean
  end

  # Multiple blank lines between comment and function


  def function_after_blank_lines do
    # This comment is inside the function
    :ok
  end

  # Helper functions used in tests
  defp validate_input, do: :ok
  defp process_data, do: :ok
  defp process_step_one(x), do: x
  defp process_step_two(x), do: x
  defp process_step_three(x), do: x
  defp do_work, do: :ok
end
