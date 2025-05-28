import { Message, AgentCard, MessageSendParams, Task, TaskStatusUpdateEvent, TaskArtifactUpdateEvent, TaskQueryParams, TaskIdParams, TaskPushNotificationConfig } from "../../schema.js";

export interface A2ARequestHandler {
    getAgentCard(): Promise<AgentCard>;

    sendMessage(
        params: MessageSendParams
    ): Promise<Message | Task>;

    sendMessageStream(
        params: MessageSendParams
    ): AsyncGenerator<
        | Message
        | Task
        | TaskStatusUpdateEvent
        | TaskArtifactUpdateEvent,
        void,
        undefined
    >;

    getTask(params: TaskQueryParams): Promise<Task>;
    cancelTask(params: TaskIdParams): Promise<Task>;

    setTaskPushNotificationConfig(
        params: TaskPushNotificationConfig
    ): Promise<TaskPushNotificationConfig>;

    getTaskPushNotificationConfig(
        params: TaskIdParams
    ): Promise<TaskPushNotificationConfig>;

    resubscribe(
        params: TaskIdParams
    ): AsyncGenerator<
        | Task
        | TaskStatusUpdateEvent
        | TaskArtifactUpdateEvent,
        void,
        undefined
    >;
}