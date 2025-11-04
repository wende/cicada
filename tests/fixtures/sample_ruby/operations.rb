# typed: true
# frozen_string_literal: true

require "sorbet-runtime"

# Module providing basic arithmetic operations
#
# This module demonstrates:
# - Module methods
# - Type signatures with Sorbet
# - Error handling
# - Private module methods
module Operations
  extend T::Sig

  # Add two numbers
  #
  # @param x [Numeric] First number
  # @param y [Numeric] Second number
  # @return [Numeric] Sum of x and y
  sig { params(x: Numeric, y: Numeric).returns(Numeric) }
  def self.add(x, y)
    x + y
  end

  # Subtract y from x
  #
  # @param x [Numeric] Number to subtract from
  # @param y [Numeric] Number to subtract
  # @return [Numeric] Difference of x and y
  sig { params(x: Numeric, y: Numeric).returns(Numeric) }
  def self.subtract(x, y)
    x - y
  end

  # Multiply two numbers
  #
  # @param x [Numeric] First number
  # @param y [Numeric] Second number
  # @return [Numeric] Product of x and y
  sig { params(x: Numeric, y: Numeric).returns(Numeric) }
  def self.multiply(x, y)
    x * y
  end

  # Divide x by y with error handling
  #
  # @param x [Numeric] Numerator
  # @param y [Numeric] Denominator
  # @return [Float] Result of division
  # @raise [ArgumentError] If y is zero
  sig { params(x: Numeric, y: Numeric).returns(Float) }
  def self.divide(x, y)
    raise ArgumentError, "Cannot divide by zero" if y.zero?

    x.to_f / y.to_f
  end

  # Calculate power (x raised to y)
  #
  # @param x [Numeric] Base
  # @param y [Numeric] Exponent
  # @return [Numeric] x raised to the power of y
  sig { params(x: Numeric, y: Numeric).returns(Numeric) }
  def self.power(x, y)
    x**y
  end

  # Calculate modulo
  #
  # @param x [Integer] Dividend
  # @param y [Integer] Divisor
  # @return [Integer] Remainder of x divided by y
  sig { params(x: Integer, y: Integer).returns(Integer) }
  def self.modulo(x, y)
    validate_positive(y)
    x % y
  end

  # Private method to validate positive numbers
  #
  # @param value [Numeric] Value to validate
  # @return [void]
  sig { params(value: Numeric).void }
  def self.validate_positive(value)
    raise ArgumentError, "Value must be positive" if value <= 0
  end

  private_class_method :validate_positive

  # Calculate absolute value
  #
  # @param x [Numeric] Number
  # @return [Numeric] Absolute value of x
  sig { params(x: Numeric).returns(Numeric) }
  def self.abs(x)
    _internal_abs(x)
  end

  # Private internal method for absolute value
  #
  # @param x [Numeric] Number
  # @return [Numeric] Absolute value
  sig { params(x: Numeric).returns(Numeric) }
  def self._internal_abs(x)
    x.abs
  end

  private_class_method :_internal_abs
end
