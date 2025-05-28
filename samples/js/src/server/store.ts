import fs from "fs/promises";
import path from "path";
import * as schema from "../schema.js";
import { A2AError } from "./error.js";
import {
  getCurrentTimestamp,
  isArtifactUpdate,
  isTaskStatusUpdate,
} from "./utils.js";

// Helper type for the simplified store
export interface TaskAndHistory {
  task: schema.Task;
  history: schema.Message[];
}

/**
 * Simplified interface for task storage providers.
 * Stores and retrieves both the task and its full message history together.
 */
export interface TaskStore {
  /**
   * Saves a task and its associated message history.
   * Overwrites existing data if the task ID exists.
   * @param data An object containing the task and its history.
   * @returns A promise resolving when the save operation is complete.
   */
  save(data: TaskAndHistory): Promise<void>;

  /**
   * Loads a task and its history by task ID.
   * @param taskId The ID of the task to load.
   * @returns A promise resolving to an object containing the Task and its history, or null if not found.
   */
  load(taskId: string): Promise<TaskAndHistory | null>;
}

// ========================
// InMemoryTaskStore
// ========================

// Use TaskAndHistory directly for storage
export class InMemoryTaskStore implements TaskStore {
  private store: Map<string, TaskAndHistory> = new Map();

  async load(taskId: string): Promise<TaskAndHistory | null> {
    const entry = this.store.get(taskId);
    // Return copies to prevent external mutation
    return entry
      ? { task: { ...entry.task }, history: [...entry.history] }
      : null;
  }

  async save(data: TaskAndHistory): Promise<void> {
    // Store copies to prevent internal mutation if caller reuses objects
    this.store.set(data.task.id, {
      task: { ...data.task },
      history: [...data.history],
    });
  }
}
