import crypto from 'node:crypto'
import type { Express } from 'express'
import type { Message, TaskStatusUpdateEvent } from '@a2a-js/sdk'

export type TaskState = TaskStatusUpdateEvent['status']['state']

export const uuid = (): string => crypto.randomUUID()

export const TERMINAL_TASK_STATES: ReadonlySet<TaskState> = new Set<TaskState>([
  'completed',
  'canceled',
  'failed',
  'rejected',
])

export function agentText(taskId: string, contextId: string, text: string): Message {
  return { kind: 'message', role: 'agent', messageId: uuid(), parts: [{ kind: 'text', text }], taskId, contextId }
}

export function statusEvent(
  taskId: string,
  contextId: string,
  state: TaskState,
  message: Message | undefined,
  final: boolean
): TaskStatusUpdateEvent {
  return {
    kind: 'status-update',
    taskId,
    contextId,
    status: { state, message, timestamp: new Date().toISOString() },
    final,
  }
}

export function requireEnv(name: string): string {
  const value = process.env[name]
  if (!value) {
    console.error(`${name} environment variable is not set.`)
    throw new Error(`${name} environment variable is not set.`)
  }
  return value
}

export function bindOrExit(app: Express, port: number, label: string, onListen: () => void): void {
  app.listen(port, onListen).on('error', (err: NodeJS.ErrnoException) => {
    console.error(`[${label}] FATAL: could not bind port ${port}: ${err.message}. Is another instance already running?`)
    process.exit(1)
  })
}
