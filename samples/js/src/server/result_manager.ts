import {
    Message,
    Task,
    TaskArtifactUpdateEvent,
    TaskStatusUpdateEvent
} from "../schema.js";
import { AgentExecutionEvent } from "./events/execution_event_bus.js";
import { TaskStore, TaskAndHistory } from "./store.js";


export class ResultManager {
    private taskStore: TaskStore;
    private currentTask?: Task;
    private latestUserMessage?: Message; // To add to history if a new task is created
    private finalMessageResult?: Message; // Stores the message if it's the final result

    constructor(taskStore: TaskStore) {
        this.taskStore = taskStore;
    }

    public setContext(latestUserMessage: Message): void {
        this.latestUserMessage = latestUserMessage;
    }

    /**
     * Processes an agent execution event and updates the task store.
     * @param event The agent execution event.
     */
    public async processEvent(event: AgentExecutionEvent): Promise<void> {
        if (event.kind === 'message') {
            this.finalMessageResult = event as Message;
            // If a message is received, it's usually the final result,
            // but we continue processing to ensure task state (if any) is also saved.
            // The ExecutionEventQueue will stop after a message event.
        } else if (event.kind === 'task') {
            const taskEvent = event as Task;
            this.currentTask = { ...taskEvent }; // Make a copy

            // Ensure the latest user message is in history if not already present
            if (this.latestUserMessage) {
                if (!this.currentTask.history?.find(msg => msg.messageId === this.latestUserMessage!.messageId)) {
                    this.currentTask.history = [this.latestUserMessage, ...(this.currentTask.history || [])];
                }
            }
            await this.saveCurrentTask();
        } else if (event.kind === 'status-update') {
            const updateEvent = event as TaskStatusUpdateEvent;
            if (this.currentTask && this.currentTask.id === updateEvent.taskId) {
                this.currentTask.status = updateEvent.status;
                if (updateEvent.status.message) {
                    // Add message to history if not already present
                    if (!this.currentTask.history?.find(msg => msg.messageId === updateEvent.status.message!.messageId)) {
                        this.currentTask.history = [...(this.currentTask.history || []), updateEvent.status.message];
                    }
                }
                await this.saveCurrentTask();
            } else if (!this.currentTask && updateEvent.taskId) {
                // Potentially an update for a task we haven't seen the 'task' event for yet,
                // or we are rehydrating. Attempt to load.
                const loaded = await this.taskStore.load(updateEvent.taskId);
                if (loaded) {
                    this.currentTask = loaded.task;
                    this.currentTask.status = updateEvent.status;
                    if (updateEvent.status.message) {
                        if (!this.currentTask.history?.find(msg => msg.messageId === updateEvent.status.message!.messageId)) {
                            this.currentTask.history = [...(this.currentTask.history || []), updateEvent.status.message];
                        }
                    }
                    await this.saveCurrentTask();
                } else {
                    console.warn(`ResultManager: Received status update for unknown task ${updateEvent.taskId}`);
                }
            }
            // If it's a final status update, the ExecutionEventQueue will stop.
            // The final result will be the currentTask.
        } else if (event.kind === 'artifact-update') {
            const artifactEvent = event as TaskArtifactUpdateEvent;
            if (this.currentTask && this.currentTask.id === artifactEvent.taskId) {
                if (!this.currentTask.artifacts) {
                    this.currentTask.artifacts = [];
                }
                const existingArtifactIndex = this.currentTask.artifacts.findIndex(
                    (art) => art.artifactId === artifactEvent.artifact.artifactId
                );
                if (existingArtifactIndex !== -1) {
                    if (artifactEvent.append) {
                        // Basic append logic, assuming parts are compatible
                        // More sophisticated merging might be needed for specific part types
                        const existingArtifact = this.currentTask.artifacts[existingArtifactIndex];
                        existingArtifact.parts.push(...artifactEvent.artifact.parts);
                        if (artifactEvent.artifact.description) existingArtifact.description = artifactEvent.artifact.description;
                        if (artifactEvent.artifact.name) existingArtifact.name = artifactEvent.artifact.name;
                        if (artifactEvent.artifact.metadata) existingArtifact.metadata = { ...existingArtifact.metadata, ...artifactEvent.artifact.metadata };

                    } else {
                        this.currentTask.artifacts[existingArtifactIndex] = artifactEvent.artifact;
                    }
                } else {
                    this.currentTask.artifacts.push(artifactEvent.artifact);
                }
                await this.saveCurrentTask();
            } else if (!this.currentTask && artifactEvent.taskId) {
                // Similar to status update, try to load if task not in memory
                const loaded = await this.taskStore.load(artifactEvent.taskId);
                if (loaded) {
                    this.currentTask = loaded.task;
                    if (!this.currentTask.artifacts) this.currentTask.artifacts = [];
                    // Apply artifact update logic (as above)
                    const existingArtifactIndex = this.currentTask.artifacts.findIndex(
                        (art) => art.artifactId === artifactEvent.artifact.artifactId
                    );
                    if (existingArtifactIndex !== -1) {
                        if (artifactEvent.append) {
                            this.currentTask.artifacts[existingArtifactIndex].parts.push(...artifactEvent.artifact.parts);
                        } else {
                            this.currentTask.artifacts[existingArtifactIndex] = artifactEvent.artifact;
                        }
                    } else {
                        this.currentTask.artifacts.push(artifactEvent.artifact);
                    }
                    await this.saveCurrentTask();
                } else {
                    console.warn(`ResultManager: Received artifact update for unknown task ${artifactEvent.taskId}`);
                }
            }
        }
    }

    private async saveCurrentTask(): Promise<void> {
        if (this.currentTask) {
            // Ensure history is part of the TaskAndHistory structure
            const taskAndHistory: TaskAndHistory = {
                task: this.currentTask,
                history: this.currentTask.history || [], // Use existing history or empty array
            };
            await this.taskStore.save(taskAndHistory);
        }
    }

    /**
     * Gets the final result, which could be a Message or a Task.
     * This should be called after the event stream has been fully processed.
     * @returns The final Message or the current Task.
     */
    public getFinalResult(): Message | Task | undefined {
        if (this.finalMessageResult) {
            return this.finalMessageResult;
        }
        return this.currentTask;
    }

    /**
     * Gets the task currently being managed by this ResultManager instance.
     * This task could be one that was started with or one created during agent execution.
     * @returns The current Task or undefined if no task is active.
     */
    public getCurrentTask(): Task | undefined {
        return this.currentTask;
    }
}