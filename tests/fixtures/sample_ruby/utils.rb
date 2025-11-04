# typed: true
# frozen_string_literal: true

require "sorbet-runtime"
require_relative "operations"

# Utility functions for array and data processing
#
# This module demonstrates:
# - Array processing methods
# - Blocks and lambdas
# - Method chaining
module Utils
  extend T::Sig

  # Calculate the average of an array of numbers
  #
  # @param numbers [Array<Numeric>] List of numbers
  # @return [Float] Average value
  sig { params(numbers: T::Array[Numeric]).returns(Float) }
  def self.average(numbers)
    return 0.0 if numbers.empty?

    sum = numbers.reduce(0) { |acc, n| Operations.add(acc, n) }
    Operations.divide(sum, numbers.length)
  end

  # Find the maximum value in an array
  #
  # @param numbers [Array<Numeric>] List of numbers
  # @return [Numeric, nil] Maximum value or nil if empty
  sig { params(numbers: T::Array[Numeric]).returns(T.nilable(Numeric)) }
  def self.max(numbers)
    return nil if numbers.empty?

    numbers.max
  end

  # Find the minimum value in an array
  #
  # @param numbers [Array<Numeric>] List of numbers
  # @return [Numeric, nil] Minimum value or nil if empty
  sig { params(numbers: T::Array[Numeric]).returns(T.nilable(Numeric)) }
  def self.min(numbers)
    return nil if numbers.empty?

    numbers.min
  end

  # Calculate the range (max - min)
  #
  # @param numbers [Array<Numeric>] List of numbers
  # @return [Numeric] Range of values
  sig { params(numbers: T::Array[Numeric]).returns(Numeric) }
  def self.range(numbers)
    return 0 if numbers.empty?

    max_val = max(numbers)
    min_val = min(numbers)
    Operations.subtract(max_val, min_val)
  end

  # Filter numbers above a threshold
  #
  # @param numbers [Array<Numeric>] List of numbers
  # @param threshold [Numeric] Threshold value
  # @return [Array<Numeric>] Filtered list
  sig { params(numbers: T::Array[Numeric], threshold: Numeric).returns(T::Array[Numeric]) }
  def self.filter_above(numbers, threshold)
    numbers.select { |n| n > threshold }
  end

  # Map numbers with a multiplier
  #
  # @param numbers [Array<Numeric>] List of numbers
  # @param multiplier [Numeric] Multiplier value
  # @return [Array<Numeric>] Transformed list
  sig { params(numbers: T::Array[Numeric], multiplier: Numeric).returns(T::Array[Numeric]) }
  def self.multiply_all(numbers, multiplier)
    numbers.map { |n| Operations.multiply(n, multiplier) }
  end

  # Sum array using reduce (demonstrating multiple ways to sum)
  #
  # @param numbers [Array<Numeric>] List of numbers
  # @return [Numeric] Sum of numbers
  sig { params(numbers: T::Array[Numeric]).returns(Numeric) }
  def self.sum_reduce(numbers)
    numbers.reduce(0) { |acc, n| Operations.add(acc, n) }
  end

  # Create a sequence from start to end
  #
  # @param start [Integer] Start value
  # @param finish [Integer] End value
  # @return [Array<Integer>] Sequence array
  sig { params(start: Integer, finish: Integer).returns(T::Array[Integer]) }
  def self.sequence(start, finish)
    (start..finish).to_a
  end

  # Private helper for validation
  #
  # @param value [T.any(T::Array[T.untyped], T.untyped)] Value to check
  # @return [Boolean] True if empty
  sig { params(value: T.any(T::Array[T.untyped], T.untyped)).returns(T::Boolean) }
  def self._empty?(value)
    value.respond_to?(:empty?) && value.empty?
  end

  private_class_method :_empty?

  # Apply a custom operation to all numbers
  #
  # @param numbers [Array<Numeric>] List of numbers
  # @param block [Proc] Block to apply
  # @return [Array<Numeric>] Transformed list
  sig { params(numbers: T::Array[Numeric], block: T.proc.params(arg0: Numeric).returns(Numeric)).returns(T::Array[Numeric]) }
  def self.apply_operation(numbers, &block)
    numbers.map(&block)
  end
end
