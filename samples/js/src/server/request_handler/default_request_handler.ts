import { v4 as uuidv4 } from 'uuid'; // For generating unique IDs

import { Message, AgentCard, PushNotificationConfig, Task, MessageSendParams, TaskState, TaskStatusUpdateEvent, TaskArtifactUpdateEvent, TaskQueryParams, TaskIdParams, TaskPushNotificationConfig } from "../../schema.js";
import { AgentExecutor } from "../agent_execution/agent_executor.js";
import { RequestContext } from "../agent_execution/request_context.js";
import { A2AError } from "../error.js";
import { ExecutionEventBusManager } from "../events/execution_event_bus_manager.js";
import { ExecutionEventQueue } from "../events/execution_event_queue.js";
import { ResultManager } from "../result_manager.js";
import { TaskStore } from "../store.js";
import { A2ARequestHandler } from "./a2a_request_handler.js";

export class DefaultRequestHandler implements A2ARequestHandler {
    private agentCard: AgentCard;
    private taskStore: TaskStore;
    private agentExecutor: AgentExecutor;
    private waitForAgentOnTaskCancellation: boolean;
    private eventBusManager: ExecutionEventBusManager;
    private cancelledTasks: Set<string> = new Set();
    // Store for push notification configurations (could be part of TaskStore or separate)
    private pushNotificationConfigs: Map<string, PushNotificationConfig> = new Map();


    constructor(
        agentCard: AgentCard,
        taskStore: TaskStore,
        agentExecutor: AgentExecutor,
        waitForAgentOnTaskCancellation: boolean = true,
    ) {
        this.agentCard = agentCard;
        this.taskStore = taskStore;
        this.agentExecutor = agentExecutor;
        this.waitForAgentOnTaskCancellation = waitForAgentOnTaskCancellation;
        this.eventBusManager = new ExecutionEventBusManager();
    }

    async getAgentCard(): Promise<AgentCard> {
        return this.agentCard;
    }

    private async _createRequestContext(
        incomingMessage: Message,
        isStream: boolean,
        resultManager: ResultManager // The ResultManager for this specific request
    ): Promise<RequestContext> {
        let task: Task | undefined;
        let referenceTasks: Task[] | undefined;

        if (incomingMessage.taskId) {
            const taskAndHistory = await this.taskStore.load(incomingMessage.taskId);
            if (!taskAndHistory) {
                throw A2AError.taskNotFound(incomingMessage.taskId);
            }
            task = taskAndHistory.task;
        }

        if (incomingMessage.referenceTaskIds && incomingMessage.referenceTaskIds.length > 0) {
            referenceTasks = [];
            for (const refId of incomingMessage.referenceTaskIds) {
                const refTaskAndHistory = await this.taskStore.load(refId);
                if (refTaskAndHistory) {
                    referenceTasks.push(refTaskAndHistory.task);
                } else {
                    console.warn(`Reference task ${refId} not found.`);
                    // Optionally, throw an error or handle as per specific requirements
                }
            }
        }

        // Ensure contextId is present
        const messageForContext = { ...incomingMessage };
        if (!messageForContext.contextId) {
            messageForContext.contextId = task?.contextId || uuidv4();
        }

        const cancellationChecker = (): boolean => {
            // Check if a task being managed by the ResultManager (potentially created later)
            // has been explicitly cancelled.
            const currentProcessingTask = resultManager.getCurrentTask();
            if (currentProcessingTask?.id && this.cancelledTasks.has(currentProcessingTask.id)) {
                return true;
            }
            return false;
        };

        return new RequestContext(
            messageForContext,
            cancellationChecker,
            task,
            referenceTasks
        );
    }


    async sendMessage(
        params: MessageSendParams
    ): Promise<Message | Task> {
        const incomingMessage = params.message;
        if (!incomingMessage.messageId) {
            throw A2AError.invalidParams('message.messageId is required.');
        }

        // Instantiate ResultManager before creating RequestContext
        const resultManager = new ResultManager(this.taskStore);
        resultManager.setContext(incomingMessage); // Set context for ResultManager

        const requestContext = await this._createRequestContext(incomingMessage, false, resultManager);
        // Use the (potentially updated) contextId from requestContext
        const finalMessageForAgent = requestContext.userMessage;


        const eventBus = this.eventBusManager.createOrGetByMessageId(
            finalMessageForAgent.messageId
        );
        const eventQueue = new ExecutionEventQueue(eventBus);

        // Start agent execution (non-blocking)
        this.agentExecutor.execute(requestContext, eventBus).catch(err => {
            console.error(`Agent execution failed for message ${finalMessageForAgent.messageId}:`, err);
            // Publish a synthetic error event if needed, or handle error reporting
            // For example, create a Task with a failed status
            const errorTask: Task = {
                id: requestContext.task?.id || uuidv4(), // Use existing task ID or generate new
                contextId: finalMessageForAgent.contextId!,
                status: {
                    state: TaskState.Failed,
                    message: {
                        kind: "message",
                        role: "agent",
                        messageId: uuidv4(),
                        parts: [{ kind: "text", text: `Agent execution error: ${err.message}` }],
                        taskId: requestContext.task?.id,
                        contextId: finalMessageForAgent.contextId!,
                    },
                    timestamp: new Date().toISOString(),
                },
                history: requestContext.task?.history ? [...requestContext.task.history] : [],
                kind: "task",
            };
            if (finalMessageForAgent) { // Add incoming message to history
                if (!errorTask.history?.find(m => m.messageId === finalMessageForAgent.messageId)) {
                    errorTask.history?.push(finalMessageForAgent);
                }
            }
            eventBus.publish(errorTask); // This will update the task store via ResultManager
            eventBus.publish({ // And publish a final status update
                kind: "status-update",
                taskId: errorTask.id,
                contextId: errorTask.contextId,
                status: errorTask.status,
                final: true,
            } as TaskStatusUpdateEvent);
        });

        for await (const event of eventQueue.events()) {
            // lastEvent is no longer needed here as ResultManager tracks the final result type
            await resultManager.processEvent(event);
            if (event.kind === 'task') {
                this.eventBusManager.associateTask(event.id, finalMessageForAgent.messageId);
            }
        }

        const finalResult = resultManager.getFinalResult();
        if (!finalResult) {
            throw A2AError.internalError('Agent execution finished without a result, and no task context found.');
        }

        // Cleanup after processing is complete for this messageId
        this.eventBusManager.cleanupByMessageId(finalMessageForAgent.messageId);
        return finalResult;
    }

    async *sendMessageStream(
        params: MessageSendParams
    ): AsyncGenerator<
        | Message
        | Task
        | TaskStatusUpdateEvent
        | TaskArtifactUpdateEvent,
        void,
        undefined
    > {
        const incomingMessage = params.message;
        if (!incomingMessage.messageId) {
            // For streams, messageId might be set by client, or server can generate if not present.
            // Let's assume client provides it or throw for now.
            throw A2AError.invalidParams('message.messageId is required for streaming.');
        }

        // Instantiate ResultManager before creating RequestContext
        const resultManager = new ResultManager(this.taskStore);
        resultManager.setContext(incomingMessage); // Set context for ResultManager

        const requestContext = await this._createRequestContext(incomingMessage, false, resultManager);
        const finalMessageForAgent = requestContext.userMessage;

        const eventBus = this.eventBusManager.createOrGetByMessageId(
            finalMessageForAgent.messageId
        );
        const eventQueue = new ExecutionEventQueue(eventBus);


        // Start agent execution (non-blocking)
        this.agentExecutor.execute(requestContext, eventBus).catch(err => {
            console.error(`Agent execution failed for stream message ${finalMessageForAgent.messageId}:`, err);
            // Publish a synthetic error event if needed
            const errorTaskStatus: TaskStatusUpdateEvent = {
                kind: "status-update",
                taskId: requestContext.task?.id || uuidv4(), // Use existing or a placeholder
                contextId: finalMessageForAgent.contextId!,
                status: {
                    state: TaskState.Failed,
                    message: {
                        kind: "message",
                        role: "agent",
                        messageId: uuidv4(),
                        parts: [{ kind: "text", text: `Agent execution error: ${err.message}` }],
                        taskId: requestContext.task?.id,
                        contextId: finalMessageForAgent.contextId!,
                    },
                    timestamp: new Date().toISOString(),
                },
                final: true, // This will terminate the stream for the client
            };
            eventBus.publish(errorTaskStatus);
        });

        try {
            for await (const event of eventQueue.events()) {
                await resultManager.processEvent(event); // Update store in background
                if (event.kind === 'task') {
                    this.eventBusManager.associateTask(event.id, finalMessageForAgent.messageId);
                }
                yield event; // Stream the event to the client
            }
        } finally {
            // Cleanup when the stream is fully consumed or breaks
            this.eventBusManager.cleanupByMessageId(finalMessageForAgent.messageId);
        }
    }

    async getTask(params: TaskQueryParams): Promise<Task> {
        const taskAndHistory = await this.taskStore.load(params.id);
        if (!taskAndHistory) {
            throw A2AError.taskNotFound(params.id);
        }
        let task = taskAndHistory.task;
        if (params.historyLength !== undefined && params.historyLength >= 0) {
            if (task.history) {
                task.history = task.history.slice(-params.historyLength);
            }
        } else {
            // Negative or invalid historyLength means no history
            task.history = [];
        }
        return task;
    }

    async cancelTask(params: TaskIdParams): Promise<Task> {
        const taskAndHistory = await this.taskStore.load(params.id);
        if (!taskAndHistory) {
            throw A2AError.taskNotFound(params.id);
        }

        const task = taskAndHistory.task;
        // Check if task is in a cancelable state
        const nonCancelableStates = [
            TaskState.Completed,
            TaskState.Failed,
            TaskState.Canceled,
            TaskState.Rejected,
        ];
        if (nonCancelableStates.includes(task.status.state)) {
            throw A2AError.taskNotCancelable(params.id);
        }

        // This would signal the agent executor that the task has been marked canceled.
        this.cancelledTasks.add(params.id);

        if (!this.waitForAgentOnTaskCancellation) {
            // Here we are marking task as cancelled. We are not waiting for the executor to actually cancel processing.
            task.status = {
                state: TaskState.Canceled,
                message: { // Optional: Add a system message indicating cancellation
                    kind: "message",
                    role: "agent",
                    messageId: uuidv4(),
                    parts: [{ kind: "text", text: "Task cancellation requested by user." }],
                    taskId: task.id,
                    contextId: task.contextId,
                },
                timestamp: new Date().toISOString(),
            };
            // Add cancellation message to history
            task.history = [...(task.history || []), task.status.message];

            await this.taskStore.save({ task, history: task.history || [] });

            // Notify active execution if any
            const eventBus = this.eventBusManager.getByTaskId(params.id);
            if (eventBus) {
                // This should be captured by ResultManager.
                eventBus.publish({
                    kind: 'status-update',
                    taskId: task.id,
                    contextId: task.contextId,
                    status: task.status,
                    final: true, // Cancellation is a final state for this execution path
                } as TaskStatusUpdateEvent);
            }
        }

        return task;
    }

    async setTaskPushNotificationConfig(
        params: TaskPushNotificationConfig
    ): Promise<TaskPushNotificationConfig> {
        if (!this.agentCard.capabilities.pushNotifications) {
            throw A2AError.pushNotificationNotSupported();
        }
        const taskAndHistory = await this.taskStore.load(params.taskId);
        if (!taskAndHistory) {
            throw A2AError.taskNotFound(params.taskId);
        }
        // Store the config. In a real app, this might be stored in the TaskStore
        // or a dedicated push notification service.
        this.pushNotificationConfigs.set(params.taskId, params.pushNotificationConfig);
        return params;
    }

    async getTaskPushNotificationConfig(
        params: TaskIdParams
    ): Promise<TaskPushNotificationConfig> {
        if (!this.agentCard.capabilities.pushNotifications) {
            throw A2AError.pushNotificationNotSupported();
        }
        const taskAndHistory = await this.taskStore.load(params.id); // Ensure task exists
        if (!taskAndHistory) {
            throw A2AError.taskNotFound(params.id);
        }
        const config = this.pushNotificationConfigs.get(params.id);
        if (!config) {
            throw A2AError.internalError(`Push notification config not found for task ${params.id}.`);
        }
        return { taskId: params.id, pushNotificationConfig: config };
    }

    async *resubscribe(
        params: TaskIdParams
    ): AsyncGenerator<
        | Task // Initial task state
        | TaskStatusUpdateEvent
        | TaskArtifactUpdateEvent,
        void,
        undefined
    > {
        if (!this.agentCard.capabilities.streaming) {
            throw A2AError.unsupportedOperation("Streaming (and thus resubscription) is not supported.");
        }

        const taskAndHistory = await this.taskStore.load(params.id);
        if (!taskAndHistory) {
            throw A2AError.taskNotFound(params.id);
        }

        // Yield the current task state first
        yield taskAndHistory.task;

        // If task is already in a final state, no more events will come.
        const finalStates = [
            TaskState.Completed, TaskState.Failed,
            TaskState.Canceled, TaskState.Rejected
        ];
        if (finalStates.includes(taskAndHistory.task.status.state)) {
            return;
        }

        const eventBus = this.eventBusManager.getByTaskId(params.id);
        if (!eventBus) {
            // No active execution for this task, so no live events.
            console.warn(`Resubscribe: No active event bus for task ${params.id}.`);
            return;
        }

        // Attach a new queue to the existing bus for this resubscription
        const eventQueue = new ExecutionEventQueue(eventBus);
        // Note: The ResultManager part is already handled by the original execution flow.
        // Resubscribe just listens for new events.

        try {
            for await (const event of eventQueue.events()) {
                // We only care about updates related to *this* task.
                // The event bus might be shared if messageId was reused, though
                // ExecutionEventBusManager tries to give one bus per original message.
                if (event.kind === 'status-update' && event.taskId === params.id) {
                    yield event as TaskStatusUpdateEvent;
                } else if (event.kind === 'artifact-update' && event.taskId === params.id) {
                    yield event as TaskArtifactUpdateEvent;
                } else if (event.kind === 'task' && event.id === params.id) {
                    // This implies the task was re-emitted, yield it.
                    yield event as Task;
                }
                // We don't yield 'message' events on resubscribe typically,
                // as those signal the end of an interaction for the *original* request.
                // If a 'message' event for the original request terminates the bus, this loop will also end.
            }
        } finally {
            eventQueue.stop();
        }
    }
}