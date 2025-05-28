import { EventEmitter } from 'events';

import {
    Message,
    Task,
    TaskStatusUpdateEvent,
    TaskArtifactUpdateEvent,
} from "../../schema.js";

export type AgentExecutionEvent =
    | Message
    | Task
    | TaskStatusUpdateEvent
    | TaskArtifactUpdateEvent;

export interface IExecutionEventBus {
    publish(event: AgentExecutionEvent): void;
    on(eventName: 'event', listener: (event: AgentExecutionEvent) => void): this;
    off(eventName: 'event', listener: (event: AgentExecutionEvent) => void): this;
    once(eventName: 'event', listener: (event: AgentExecutionEvent) => void): this;
    removeAllListeners(eventName?: 'event'): this;
}

export class ExecutionEventBus extends EventEmitter implements IExecutionEventBus {
    constructor() {
        super();
    }

    publish(event: AgentExecutionEvent): void {
        this.emit('event', event);
    }
}
