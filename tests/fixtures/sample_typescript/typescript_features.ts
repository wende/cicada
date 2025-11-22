/**
 * TypeScript-specific features for comprehensive testing.
 *
 * This module demonstrates interfaces, generics, async/await,
 * arrow functions, static methods, and type aliases.
 */

import { add } from "./operations";

/**
 * Interface for data processing.
 */
export interface DataProcessor<T> {
  process(data: T): T;
  validate(data: T): boolean;
}

/**
 * Type alias for result objects.
 */
export type ProcessResult<T> = {
  success: boolean;
  data: T;
  timestamp: number;
};

/**
 * Generic container class with type parameter.
 *
 * @template T - The type of data stored in the container
 */
export class Container<T> {
  private items: T[];
  private static instanceCount: number = 0;

  /**
   * Create a new container.
   *
   * @param initialItems - Initial items to store
   */
  constructor(initialItems: T[] = []) {
    this.items = initialItems;
    Container.instanceCount++;
  }

  /**
   * Static method to get instance count.
   *
   * @returns Number of Container instances created
   */
  static getInstanceCount(): number {
    return Container.instanceCount;
  }

  /**
   * Static method to reset instance count.
   */
  static resetCount(): void {
    Container.instanceCount = 0;
  }

  /**
   * Add an item to the container.
   *
   * @param item - Item to add
   */
  add(item: T): void {
    this.items.push(item);
  }

  /**
   * Get all items from the container.
   *
   * @returns Array of items
   */
  getAll(): T[] {
    return [...this.items];
  }

  /**
   * Private method to validate item.
   */
  private _validateItem(item: T): boolean {
    return item !== null && item !== undefined;
  }
}

/**
 * Async function that processes data with delay.
 *
 * @param data - Data to process
 * @param delayMs - Delay in milliseconds
 * @returns Processed data wrapped in Promise
 */
export async function asyncProcess<T>(
  data: T,
  delayMs: number = 100
): Promise<ProcessResult<T>> {
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve({
        success: true,
        data: data,
        timestamp: Date.now(),
      });
    }, delayMs);
  });
}

/**
 * Async function that fetches data from a source.
 *
 * @param id - Data identifier
 * @returns Fetched data or null
 */
export async function fetchData(id: string): Promise<string | null> {
  // Simulate async fetch
  await asyncProcess(id, 50);
  return `data-${id}`;
}

/**
 * Arrow function exported as const.
 */
export const arrowAdd = (x: number, y: number): number => {
  return add(x, y); // Cross-file call
};

/**
 * Arrow function with implicit return.
 */
export const arrowMultiply = (x: number, y: number): number => x * y;

/**
 * Higher-order arrow function.
 */
export const createAdder = (base: number): ((x: number) => number) => {
  return (x: number) => x + base;
};

/**
 * Generic function to map array elements.
 *
 * @template T, U
 * @param items - Input array
 * @param mapper - Mapping function
 * @returns Mapped array
 */
export function mapItems<T, U>(items: T[], mapper: (item: T) => U): U[] {
  return items.map(mapper);
}

/**
 * Generic function with constraint.
 *
 * @template T
 * @param item - Item with length property
 * @returns Length of the item
 */
export function getLength<T extends { length: number }>(item: T): number {
  return item.length;
}

/**
 * Implementation of DataProcessor interface.
 */
export class StringProcessor implements DataProcessor<string> {
  /**
   * Process string data by trimming and uppercasing.
   *
   * @param data - Input string
   * @returns Processed string
   */
  process(data: string): string {
    return data.trim().toUpperCase();
  }

  /**
   * Validate string data is not empty.
   *
   * @param data - Input string
   * @returns True if valid
   */
  validate(data: string): boolean {
    return data.length > 0;
  }

  /**
   * Private helper method.
   */
  private _normalize(data: string): string {
    return data.toLowerCase();
  }
}

/**
 * Class with async methods.
 */
export class AsyncHandler {
  private data: Map<string, any>;

  constructor() {
    this.data = new Map();
  }

  /**
   * Async method to save data.
   *
   * @param key - Data key
   * @param value - Data value
   * @returns Success status
   */
  async save(key: string, value: any): Promise<boolean> {
    await asyncProcess(value);
    this.data.set(key, value);
    return true;
  }

  /**
   * Async method to load data.
   *
   * @param key - Data key
   * @returns Loaded value or null
   */
  async load(key: string): Promise<any | null> {
    const value = this.data.get(key);
    await asyncProcess(value);
    return value || null;
  }

  /**
   * Private async helper.
   */
  private async _internalAsync(key: string): Promise<void> {
    await this.load(key);
  }
}

/**
 * Private interface (not exported).
 */
interface InternalConfig {
  enabled: boolean;
  timeout: number;
}

/**
 * Private class (not exported).
 */
/**
 * Private arrow function (not exported).
 */
const _privateArrow = (x: number): number => x * 2;

/**
 * Private async function (not exported).
 */
async function _privateAsync(): Promise<void> {
  await asyncProcess("internal", 10);
}
