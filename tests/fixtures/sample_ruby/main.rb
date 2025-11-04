# typed: true
# frozen_string_literal: true

require "sorbet-runtime"
require_relative "calculator"
require_relative "operations"
require_relative "utils"
require_relative "formatter"

# Main entry point demonstrating usage of all modules
#
# This file shows:
# - Cross-file dependencies
# - Multiple calls to the same functions
# - Usage of class and module methods
class Main
  extend T::Sig

  # Run sample calculations using all modules
  #
  # @return [void]
  sig { void }
  def self.run_calculations
    # Create calculator instance
    calc = Calculator.new(10)

    # Multiple calls to the same method
    result1 = calc.add(5, 3) # First call
    result2 = calc.add(10, 20) # Second call
    result3 = calc.add(result1, result2) # Third call

    # Direct calls to Operations module
    sum_val = Operations.add(100, 200)
    diff = Operations.subtract(sum_val, 50)
    product = Operations.multiply(diff, 2)

    # Use Utils module
    numbers = [1, 2, 3, 4, 5]
    avg = Utils.average(numbers)
    max_val = Utils.max(numbers)
    min_val = Utils.min(numbers)

    # Multiple calls to calc methods
    calc.multiply(5, 6)
    calc.multiply(3, 4)
    calc.divide(100, 4)

    # Format results
    formatted_avg = Formatter.format_number(avg)
    formatted_currency = Formatter.format_currency(product)

    puts "Results: #{result3}, #{product}, #{formatted_avg}, #{formatted_currency}"
  end

  # Process data from an array
  #
  # @param data [Array<Numeric>] Input data
  # @return [Hash] Processed results
  sig { params(data: T::Array[Numeric]).returns(T::Hash[Symbol, T.any(Numeric, String)]) }
  def self.process_data(data)
    return {} if data.empty?

    total = Utils.sum_reduce(data)
    avg = Utils.average(data)
    range = Utils.range(data)

    {
      total: total,
      average: avg,
      range: range,
      formatted_total: Formatter.format_number(total)
    }
  end

  # Demonstrate complex calculations
  #
  # @return [void]
  sig { void }
  def self.demonstrate_complex
    calc = Calculator.with_preset(100)

    # Multiple operations
    result = calc.calculate_expression(10, 20, 5)
    formatted = calc.format_value

    # Array operations
    numbers = Utils.sequence(1, 10)
    filtered = Utils.filter_above(numbers, 5)
    multiplied = Utils.multiply_all(filtered, 2)
    final_sum = calc.sum_array(multiplied)

    puts "Complex result: #{result}, Final sum: #{final_sum}"
  end

  # Private helper function
  #
  # @param x [Numeric] First number
  # @param y [Numeric] Second number
  # @return [Numeric] Sum
  sig { params(x: Numeric, y: Numeric).returns(Numeric) }
  def self._internal_helper(x, y)
    Operations.add(x, y)
  end

  private_class_method :_internal_helper
end

# Top-level function to run the main program
#
# @return [void]
sig { void }
def run_program
  Main.run_calculations
  sample_data = [10, 20, 30, 40, 50]
  results = Main.process_data(sample_data)
  puts "Data processing results: #{results}"
  Main.demonstrate_complex
end

# Execute if this is the main file
run_program if __FILE__ == $PROGRAM_NAME
