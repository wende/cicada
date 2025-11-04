# typed: true
# frozen_string_literal: true

require "sorbet-runtime"

# Module for formatting numbers and results
#
# This module demonstrates:
# - String interpolation
# - Conditional logic
# - Module constants
module Formatter
  extend T::Sig

  DECIMAL_PLACES = 2
  CURRENCY_SYMBOL = "$"

  # Format a number with decimal places
  #
  # @param number [Numeric] Number to format
  # @return [String] Formatted number string
  sig { params(number: Numeric).returns(String) }
  def self.format_number(number)
    "%.#{DECIMAL_PLACES}f" % number
  end

  # Format a number as currency
  #
  # @param amount [Numeric] Amount to format
  # @return [String] Formatted currency string
  sig { params(amount: Numeric).returns(String) }
  def self.format_currency(amount)
    "#{CURRENCY_SYMBOL}#{format_number(amount)}"
  end

  # Format a percentage
  #
  # @param value [Numeric] Value to format as percentage
  # @return [String] Formatted percentage string
  sig { params(value: Numeric).returns(String) }
  def self.format_percentage(value)
    "#{format_number(value * 100)}%"
  end

  # Format with units
  #
  # @param value [Numeric] Value to format
  # @param unit [String] Unit suffix
  # @return [String] Formatted string with unit
  sig { params(value: Numeric, unit: String).returns(String) }
  def self.format_with_unit(value, unit)
    "#{format_number(value)} #{unit}"
  end

  # Format a large number with commas
  #
  # @param number [Numeric] Number to format
  # @return [String] Formatted number with thousand separators
  sig { params(number: Numeric).returns(String) }
  def self.format_with_separators(number)
    _add_thousand_separators(number.to_s)
  end

  # Private helper to add thousand separators
  #
  # @param number_str [String] Number as string
  # @return [String] Number with separators
  sig { params(number_str: String).returns(String) }
  def self._add_thousand_separators(number_str)
    # Split into integer and decimal parts
    parts = number_str.split(".")
    integer_part = parts[0]
    decimal_part = parts[1]

    # Add commas to integer part
    formatted = integer_part.reverse.scan(/.{1,3}/).join(",").reverse

    # Rejoin with decimal if present
    decimal_part ? "#{formatted}.#{decimal_part}" : formatted
  end

  private_class_method :_add_thousand_separators
end
