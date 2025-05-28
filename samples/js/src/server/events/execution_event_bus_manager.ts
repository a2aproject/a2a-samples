import { ExecutionEventBus, IExecutionEventBus } from "./execution_event_bus.js";

export class ExecutionEventBusManager {
    private messageIdToBus: Map<string, IExecutionEventBus> = new Map();
    private taskIdToMessageId: Map<string, string> = new Map();

    /**
     * Creates or retrieves an existing ExecutionEventBus based on the messageId.
     * @param messageId The ID of the message.
     * @returns An instance of IExecutionEventBus.
     */
    public createOrGetByMessageId(messageId: string): IExecutionEventBus {
        if (!this.messageIdToBus.has(messageId)) {
            this.messageIdToBus.set(messageId, new ExecutionEventBus());
        }
        return this.messageIdToBus.get(messageId)!;
    }

    /**
     * Associates a taskId with a messageId.
     * This allows retrieving the event bus using the taskId.
     * @param taskId The ID of the task.
     * @param messageId The ID of the message that initiated the task.
     */
    public associateTask(taskId: string, messageId: string): void {
        if (this.messageIdToBus.has(messageId)) {
            this.taskIdToMessageId.set(taskId, messageId);
        } else {
            console.warn(
                `ExecutionEventBusManager: Cannot associate task ${taskId}. No event bus found for messageId ${messageId}.`
            );
        }
    }

    /**
     * Retrieves an existing ExecutionEventBus based on the taskId.
     * @param taskId The ID of the task.
     * @returns An instance of IExecutionEventBus or undefined if not found.
     */
    public getByTaskId(taskId: string): IExecutionEventBus | undefined {
        const messageId = this.taskIdToMessageId.get(taskId);
        if (messageId) {
            return this.messageIdToBus.get(messageId);
        }
        return undefined;
    }

    /**
     * Removes the event bus and any associations for a given messageId.
     * This should be called when an execution flow is complete to free resources.
     * @param messageId The ID of the message.
     */
    public cleanupByMessageId(messageId: string): void {
        const bus = this.messageIdToBus.get(messageId);
        if (bus) {
            bus.removeAllListeners();
        }
        this.messageIdToBus.delete(messageId);
        // Also remove any taskId associations
        for (const [taskId, msgId] of this.taskIdToMessageId.entries()) {
            if (msgId === messageId) {
                this.taskIdToMessageId.delete(taskId);
            }
        }
    }
}