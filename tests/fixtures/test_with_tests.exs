defmodule SampleTest do
  use ExUnit.Case

  describe "basic math operations" do
    test "addition works correctly" do
      assert 1 + 1 == 2
    end

    test "subtraction works correctly" do
      assert 5 - 3 == 2
    end
  end

  describe "string operations" do
    test "concatenation works" do
      assert "hello" <> " world" == "hello world"
    end
  end

  test "standalone test without describe" do
    assert true
  end

  defp helper_function do
    :ok
  end
end
