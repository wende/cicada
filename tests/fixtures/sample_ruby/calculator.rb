# typed: true
# frozen_string_literal: true

require "sorbet-runtime"
require_relative "operations"
require_relative "formatter"

# A simple calculator that performs basic arithmetic operations
#
# This class demonstrates various Ruby features:
# - Instance methods (public and private)
# - Class methods
# - Attr accessors
# - Cross-file method calls
# - Type annotations with Sorbet
class Calculator
  extend T::Sig

  attr_reader :value

  sig { params(initial_value: Numeric).void }
  def initialize(initial_value = 0)
    @value = T.let(initial_value, Numeric)
  end

  # Add two numbers using the Operations module
  #
  # @param x [Numeric] First number
  # @param y [Numeric] Second number
  # @return [Numeric] Sum of x and y
  sig { params(x: Numeric, y: Numeric).returns(Numeric) }
  def add(x, y)
    Operations.add(x, y) # Cross-file call
  end

  # Multiply two numbers using the Operations module
  #
  # @param x [Numeric] First number
  # @param y [Numeric] Second number
  # @return [Numeric] Product of x and y
  sig { params(x: Numeric, y: Numeric).returns(Numeric) }
  def multiply(x, y)
    Operations.multiply(x, y) # Cross-file call
  end

  # Divide x by y
  #
  # @param x [Numeric] Numerator
  # @param y [Numeric] Denominator
  # @return [Float] Result of division
  sig { params(x: Numeric, y: Numeric).returns(Float) }
  def divide(x, y)
    Operations.divide(x, y) # Cross-file call
  end

  # Sum an array of numbers
  #
  # @param numbers [Array<Numeric>] List of numbers
  # @return [Numeric] Sum of all numbers
  sig { params(numbers: T::Array[Numeric]).returns(Numeric) }
  def sum_array(numbers)
    numbers.reduce(0) { |acc, n| add(acc, n) } # Multiple calls to add
  end

  # Format the current value
  #
  # @return [String] Formatted value
  sig { returns(String) }
  def format_value
    Formatter.format_number(@value) # Cross-file call
  end

  # Calculate a complex expression: (x + y) * z
  #
  # @param x [Numeric] First operand
  # @param y [Numeric] Second operand
  # @param z [Numeric] Third operand
  # @return [Numeric] Result of (x + y) * z
  sig { params(x: Numeric, y: Numeric, z: Numeric).returns(Numeric) }
  def calculate_expression(x, y, z)
    sum_result = add(x, y) # First call
    multiply(sum_result, z) # Second call
  end

  # Class method to create a calculator with a preset value
  #
  # @param preset [Numeric] Preset value
  # @return [Calculator] New calculator instance
  sig { params(preset: Numeric).returns(Calculator) }
  def self.with_preset(preset)
    new(preset)
  end

  # Class method to perform quick addition
  #
  # @param x [Numeric] First number
  # @param y [Numeric] Second number
  # @return [Numeric] Sum of x and y
  sig { params(x: Numeric, y: Numeric).returns(Numeric) }
  def self.quick_add(x, y)
    Operations.add(x, y)
  end

  private

  # Private method for internal calculations
  #
  # @return [String] Internal state
  sig { returns(String) }
  def internal_state
    "value: #{@value}"
  end

  # Private method to validate input
  #
  # @param value [Numeric] Value to validate
  # @return [Boolean] True if valid
  sig { params(value: Numeric).returns(T::Boolean) }
  def valid_input?(value)
    !value.nil? && value.is_a?(Numeric)
  end
end

# Top-level helper function to demonstrate module-level methods
#
# @param numbers [Array<Numeric>] List of numbers
# @return [Float] Average of the numbers
sig { params(numbers: T::Array[Numeric]).returns(Float) }
def calculate_average(numbers)
  return 0.0 if numbers.empty?

  sum = numbers.reduce(0) { |acc, n| Operations.add(acc, n) }
  Operations.divide(sum, numbers.length)
end

# Private top-level function
#
# @return [String] A private message
sig { returns(String) }
def _private_helper
  "This is a private helper"
end
