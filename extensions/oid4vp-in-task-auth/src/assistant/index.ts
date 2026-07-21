import express from 'express'
import { AgentCard, Message, Task, TaskStatusUpdateEvent, TextPart } from '@a2a-js/sdk'
import {
  AgentExecutor,
  DefaultRequestHandler,
  ExecutionEventBus,
  InMemoryTaskStore,
  RequestContext,
  TaskStore,
} from '@a2a-js/sdk/server'
import { A2AExpressApp } from '@a2a-js/sdk/server/express'
import { A2AClient } from '@a2a-js/sdk/client'
import * as dotenv from 'dotenv'
import { IN_TASK_OID4VP_EXTENSION_URI, InTaskOpenId4VpExtension, InTaskOpenId4VpMessageMetadata } from '../extension'
import { agentText, bindOrExit, statusEvent, TERMINAL_TASK_STATES, uuid } from '../a2a-helpers'

dotenv.config()

const ASSISTANT_A2A_PORT = Number(process.env.ASSISTANT_AGENT_PORT) || 10004
const MERCHANT_URL = process.env.MERCHANT_AGENT_URL || 'http://localhost:10003'

const ASSISTANT_AGENT_CARD: AgentCard = {
  name: 'Travel Assistant',
  description: "A personal assistant agent that books travel on the user's behalf via partner agents.",
  url: `http://localhost:${ASSISTANT_A2A_PORT}/`,
  provider: { organization: 'A2A Samples', url: 'https://example.com/a2a-samples' },
  version: '1.0.0',
  protocolVersion: '1.0',
  capabilities: {
    streaming: true,
    extensions: [
      {
        uri: IN_TASK_OID4VP_EXTENSION_URI,
        description:
          'Supports OID4VP In-Task Authorization extension, main purpose is relaying presentation between the user and downstream agents',
        required: false,
        params: { oid4vpVersions: ['1.0'] },
      } satisfies InTaskOpenId4VpExtension,
    ],
  },
  defaultInputModes: ['text'],
  defaultOutputModes: ['text'],
  skills: [
    {
      id: 'travel-assistant',
      name: 'Book travel on your behalf',
      description: 'Forwards your booking requests to partner booking agents and relays any authorization back to you.',
      tags: ['assistant', 'travel', 'delegation'],
      examples: ['Book a hotel for Saturday and apply my partner discount'],
      inputModes: ['text'],
      outputModes: ['text'],
    },
  ],
}

interface MerchantTaskRef {
  taskId?: string
  contextId?: string
}

class AssistantAgentExecutor implements AgentExecutor {
  private readonly cancelledTasks = new Set<string>()
  private merchantClient?: A2AClient
  private readonly merchantTasks = new Map<string, MerchantTaskRef>()

  public cancelTask = async (taskId: string): Promise<void> => {
    this.cancelledTasks.add(taskId)
  }

  private async getMerchantClient(): Promise<A2AClient> {
    if (!this.merchantClient) {
      this.merchantClient = await A2AClient.fromCardUrl(`${MERCHANT_URL}/.well-known/agent-card.json`)
    }
    return this.merchantClient
  }

  public async execute(requestContext: RequestContext, eventBus: ExecutionEventBus): Promise<void> {
    const userMessage = requestContext.userMessage
    let task = requestContext.task

    const taskId = task?.id || uuid()
    const contextId = userMessage.contextId || task?.contextId || uuid()
    const userText = (userMessage.parts.find((p): p is TextPart => p.kind === 'text')?.text ?? '').trim()

    console.log(
      `[Assistant] User message ${userMessage.messageId} (task ${taskId}, context ${contextId}): "${userText}"`
    )

    if (!task) {
      task = {
        kind: 'task',
        id: taskId,
        contextId,
        status: { state: 'submitted', timestamp: new Date().toISOString() },
        history: [userMessage],
        metadata: userMessage.metadata,
      }
      eventBus.publish(task)
    }

    eventBus.publish(
      statusEvent(
        taskId,
        contextId,
        'working',
        agentText(taskId, contextId, 'Forwarding your request to BlueSky Stays on your behalf...'),
        false
      )
    )

    try {
      await this.forwardAndRelay(userText, taskId, contextId, eventBus)
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Unknown error'
      console.error(`[Assistant] Error talking to the merchant:`, error)
      eventBus.publish(
        statusEvent(
          taskId,
          contextId,
          'failed',
          agentText(taskId, contextId, `Sorry, I couldn't reach the booking agent: ${message}`),
          true
        )
      )
    }
  }

  private async forwardAndRelay(
    userText: string,
    taskId: string,
    contextId: string,
    eventBus: ExecutionEventBus
  ): Promise<void> {
    const merchantClient = await this.getMerchantClient()

    const ref = this.merchantTasks.get(contextId) ?? {}
    const forwarded: Message = {
      messageId: uuid(),
      kind: 'message',
      role: 'user',
      parts: [{ kind: 'text', text: userText }],
      ...(ref.taskId ? { taskId: ref.taskId } : {}),
      ...(ref.contextId ? { contextId: ref.contextId } : {}),
    }

    for await (const event of merchantClient.sendMessageStream({ message: forwarded })) {
      if (this.cancelledTasks.has(taskId)) {
        eventBus.publish(statusEvent(taskId, contextId, 'canceled', undefined, true))
        return
      }

      if (event.kind === 'task') {
        const merchantTask = event as Task
        this.merchantTasks.set(contextId, { taskId: merchantTask.id, contextId: merchantTask.contextId })
        continue
      }

      if (event.kind === 'status-update') {
        const taskStatusUpdateEvent = event as TaskStatusUpdateEvent
        const terminal = taskStatusUpdateEvent.final && TERMINAL_TASK_STATES.has(taskStatusUpdateEvent.status.state)
        this.merchantTasks.set(contextId, {
          taskId: terminal ? undefined : taskStatusUpdateEvent.taskId,
          contextId: taskStatusUpdateEvent.contextId,
        })

        if (taskStatusUpdateEvent.status.state === 'auth-required') {
          this.relayAuthRequired(taskStatusUpdateEvent, taskId, contextId, eventBus)
          continue
        }

        eventBus.publish(
          statusEvent(
            taskId,
            contextId,
            taskStatusUpdateEvent.status.state,
            this.rewriteMessage(taskStatusUpdateEvent.status.message, taskId, contextId),
            taskStatusUpdateEvent.final
          )
        )
      } else if (event.kind === 'message') {
        const message = event as Message
        if (message.contextId) this.merchantTasks.set(contextId, { taskId: message.taskId, contextId: message.contextId })
        eventBus.publish(statusEvent(taskId, contextId, 'working', this.rewriteMessage(message, taskId, contextId), false))
      }
    }
  }

  private relayAuthRequired(
    merchantEvent: TaskStatusUpdateEvent,
    taskId: string,
    contextId: string,
    eventBus: ExecutionEventBus
  ): void {
    const metadata = merchantEvent.status.message?.metadata?.[IN_TASK_OID4VP_EXTENSION_URI] as
      | InTaskOpenId4VpMessageMetadata
      | undefined

    if (!metadata?.authorizationRequest) {
      console.warn('[Assistant] auth-required without OID4VP metadata — forwarding the status unchanged.')
      eventBus.publish(
        statusEvent(
          taskId,
          contextId,
          'auth-required',
          this.rewriteMessage(merchantEvent.status.message, taskId, contextId),
          false
        )
      )
      return
    }

    console.log(
      "[Assistant] Merchant requires a credential. I am not the holder of the user's vouchers → relaying upstream."
    )

    eventBus.publish({
      kind: 'status-update',
      taskId,
      contextId,
      status: {
        state: 'auth-required',
        message: {
          kind: 'message',
          role: 'agent',
          messageId: uuid(),
          parts: [
            {
              kind: 'text',
              text: "BlueSky Stays needs a partner discount voucher. I don't hold your vouchers, so please present one from your wallet.",
            },
          ],
          taskId,
          contextId,
          metadata: {
            [IN_TASK_OID4VP_EXTENSION_URI]: {
              authorizationRequest: metadata.authorizationRequest,
            } satisfies InTaskOpenId4VpMessageMetadata,
          },
        },
        timestamp: new Date().toISOString(),
      },
      final: false,
    })
  }

  private rewriteMessage(message: Message | undefined, taskId: string, contextId: string): Message | undefined {
    if (!message) return undefined
    return { ...message, taskId, contextId }
  }
}

async function main() {
  const taskStore: TaskStore = new InMemoryTaskStore()
  const agentExecutor = new AssistantAgentExecutor()

  const requestHandler = new DefaultRequestHandler(ASSISTANT_AGENT_CARD, taskStore, agentExecutor)
  const appBuilder = new A2AExpressApp(requestHandler)
  const expressApp = appBuilder.setupRoutes(express())

  bindOrExit(expressApp, ASSISTANT_A2A_PORT, 'Assistant', () => {
    console.log(`[Assistant] Travel Assistant A2A server started on http://localhost:${ASSISTANT_A2A_PORT}`)
    console.log(`[Assistant] Forwarding booking requests to merchant at ${MERCHANT_URL}`)
    console.log(`[Assistant] Agent Card: http://localhost:${ASSISTANT_A2A_PORT}/.well-known/agent-card.json`)
  })
}

main().catch(console.error)
