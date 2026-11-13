/* eslint-disable n/no-missing-import, n/no-process-exit */
import crypto from "node:crypto";
import type { Express } from "express";
import {
    Message,
    Part,
    Role,
    TaskState,
    TaskStatusUpdateEvent,
} from "@a2a-js/sdk";

export const uuid = (): string => crypto.randomUUID();

export const TERMINAL_TASK_STATES: ReadonlySet<TaskState> = new Set<TaskState>([
    TaskState.TASK_STATE_COMPLETED,
    TaskState.TASK_STATE_CANCELED,
    TaskState.TASK_STATE_FAILED,
    TaskState.TASK_STATE_REJECTED,
]);

export function textPart(text: string): Part {
    return {
        content: { $case: "text", value: text },
        metadata: undefined,
        filename: "",
        mediaType: "text/plain",
    };
}

/** Concatenates the text of every text part, ignoring non-text content. */
export function partsToText(parts: Part[]): string {
    return parts
        .map((part) =>
            part.content?.$case === "text" ? part.content.value : ""
        )
        .join("");
}

export function agentText(
    taskId: string,
    contextId: string,
    text: string
): Message {
    return {
        messageId: uuid(),
        contextId,
        taskId,
        role: Role.ROLE_AGENT,
        parts: [textPart(text)],
        metadata: undefined,
        extensions: [],
        referenceTaskIds: [],
    };
}

export function statusEvent(
    taskId: string,
    contextId: string,
    state: TaskState,
    message: Message | undefined
): TaskStatusUpdateEvent {
    return {
        taskId,
        contextId,
        status: { state, message, timestamp: new Date().toISOString() },
        metadata: undefined,
    };
}

export function requireEnv(name: string): string {
    const value = process.env[name];
    if (!value) {
        console.error(`${name} environment variable is not set.`);
        throw new Error(`${name} environment variable is not set.`);
    }
    return value;
}

export function bindOrExit(
    app: Express,
    port: number,
    label: string,
    onListen: () => void
): void {
    app.listen(port, onListen).on("error", (err: NodeJS.ErrnoException) => {
        console.error(
            `[${label}] FATAL: could not bind port ${port}: ${err.message}. Is another instance already running?`
        );
        process.exit(1);
    });
}
