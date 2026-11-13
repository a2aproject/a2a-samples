package com.google.a2a.server;

import com.google.a2a.model.Task;
import com.google.a2a.model.Message;

/**
 * TaskHandler is a functional interface for handling tasks
 */
@FunctionalInterface
public interface TaskHandler {
    /**
     * Handle a task
     * 
     * @param task the task to handle
     * @param message the message content
     * @return the processed task
     * @throws Exception exceptions during processing
     */
    Task handle(Task task, Message message) throws Exception;
} 