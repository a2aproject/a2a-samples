import {
    TaskStatusUpdateEvent,
} from "../../schema.js";
import { IExecutionEventBus, AgentExecutionEvent } from "./execution_event_bus.js";

/**
 * An async queue that subscribes to an ExecutionEventBus for events
 * and provides an async generator to consume them.
 */
export class ExecutionEventQueue {
    private eventBus: IExecutionEventBus;
    private eventQueue: AgentExecutionEvent[] = [];
    private resolvePromise?: (value: void | PromiseLike<void>) => void;
    private stopped: boolean = false;
    private boundHandleEvent: (event: AgentExecutionEvent) => void;


    constructor(eventBus: IExecutionEventBus) {
        this.eventBus = eventBus;
        this.boundHandleEvent = this.handleEvent.bind(this);
        this.eventBus.on('event', this.boundHandleEvent);
    }

    private handleEvent(event: AgentExecutionEvent): void {
        if (this.stopped) return;
        this.eventQueue.push(event);
        if (this.resolvePromise) {
            this.resolvePromise();
            this.resolvePromise = undefined;
        }
    }

    /**
     * Provides an async generator that yields events from the event bus.
     * Stops when a Message event is received or a TaskStatusUpdateEvent with final=true is received.
     */
    public async *events(): AsyncGenerator<AgentExecutionEvent, void, undefined> {
        while (!this.stopped) {
            if (this.eventQueue.length > 0) {
                const event = this.eventQueue.shift()!;
                yield event;
                if (event.kind === 'message' || (
                    event.kind === 'status-update' &&
                    (event as TaskStatusUpdateEvent).final
                )) {
                    this.stop();
                    break;
                }
            } else {
                await new Promise<void>((resolve) => {
                    this.resolvePromise = resolve;
                });
            }
        }
    }

    /**
     * Stops the event queue from processing further events.
     */
    public stop(): void {
        this.stopped = true;
        if (this.resolvePromise) {
            this.resolvePromise(); // Unblock any pending await
            this.resolvePromise = undefined;
        }

        this.eventBus.off('event', this.boundHandleEvent);
    }
}
