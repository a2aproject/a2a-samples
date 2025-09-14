import express from "express";
import { v4 as uuidv4 } from "uuid"; // For generating unique IDs

import {
  AgentCard,
  Task,
  TaskStatusUpdateEvent,
  TextPart,
  Message,
} from "@a2a-js/sdk";
import {
  InMemoryTaskStore,
  TaskStore,
  AgentExecutor,
  RequestContext,
  ExecutionEventBus,
  DefaultRequestHandler,
} from "@a2a-js/sdk/server"; // Import server components
import { A2AExpressApp } from "@a2a-js/sdk/server/express";
import { MessageData } from "genkit";
import { ai } from "./genkit.js";

import * as dotenv from "dotenv";
dotenv.config();

if (!process.env.GOOGLE_API_KEY) {
  console.error("GOOGLE_API_KEY environment variable is not set.");
  throw new Error("GOOGLE_API_KEY environment variable is not set.");
}

const contentEditorPrompt = ai.prompt("content_editor");

class ContentEditorAgentExecutor implements AgentExecutor {
  private cancelledTasks = new Set<string>();

  public cancelTask = async (
    taskId: string,
    eventBus: ExecutionEventBus,
  ): Promise<void> => {
    this.cancelledTasks.add(taskId);
  };

  async execute(
    requestContext: RequestContext,
    eventBus: ExecutionEventBus,
  ): Promise<void> {
    const userMessage = requestContext.userMessage;
    const existingTask = requestContext.task;

    const taskId = existingTask?.id || uuidv4();
    const contextId =
      userMessage.contextId || existingTask?.contextId || uuidv4();

    console.log(
      `[ContentEditorAgentExecutor] Processing message ${userMessage.messageId} for task ${taskId} (context: ${contextId})`,
    );

    if (!existingTask) {
      const initialTask: Task = {
        kind: "task",
        id: taskId,
        contextId: contextId,
        status: {
          state: "submitted",
          timestamp: new Date().toISOString(),
        },
        history: [userMessage],
        metadata: userMessage.metadata,
      };
      eventBus.publish(initialTask);
    }

    const workingStatusUpdate: TaskStatusUpdateEvent = {
      kind: "status-update",
      taskId: taskId,
      contextId: contextId,
      status: {
        state: "working",
        message: {
          kind: "message",
          role: "agent",
          messageId: uuidv4(),
          parts: [{ kind: "text", text: "Editing content..." }],
          taskId: taskId,
          contextId: contextId,
        },
        timestamp: new Date().toISOString(),
      },
      final: false,
    };
    eventBus.publish(workingStatusUpdate);

    const historyForGenkit = existingTask?.history
      ? [...existingTask.history]
      : [];
    if (!historyForGenkit.find((m) => m.messageId === userMessage.messageId)) {
      historyForGenkit.push(userMessage);
    }

    const messages: MessageData[] = historyForGenkit
      .map((m) => ({
        role: (m.role === "agent" ? "model" : "user") as "user" | "model",
        content: m.parts
          .filter(
            (p): p is TextPart => p.kind === "text" && !!(p as TextPart).text,
          )
          .map((p) => ({
            text: (p as TextPart).text,
          })),
      }))
      .filter((m) => m.content.length > 0);

    if (messages.length === 0) {
      console.warn(
        `[ContentEditorAgentExecutor] No valid text messages found in history for task ${taskId}.`,
      );
      const failureUpdate: TaskStatusUpdateEvent = {
        kind: "status-update",
        taskId: taskId,
        contextId: contextId,
        status: {
          state: "failed",
          message: {
            kind: "message",
            role: "agent",
            messageId: uuidv4(),
            parts: [{ kind: "text", text: "No message found to process." }],
            taskId: taskId,
            contextId: contextId,
          },
          timestamp: new Date().toISOString(),
        },
        final: true,
      };
      eventBus.publish(failureUpdate);
      return;
    }

    try {
      const response = await contentEditorPrompt(
        {},
        {
          messages,
        },
      );

      if (this.cancelledTasks.has(taskId)) {
        console.log(
          `[ContentEditorAgentExecutor] Request cancelled for task: ${taskId}`,
        );

        const cancelledUpdate: TaskStatusUpdateEvent = {
          kind: "status-update",
          taskId: taskId,
          contextId: contextId,
          status: {
            state: "canceled",
            timestamp: new Date().toISOString(),
          },
          final: true,
        };
        eventBus.publish(cancelledUpdate);
        return;
      }

      const responseText = response.text;
      console.info(
        `[ContentEditorAgentExecutor] Prompt response: ${responseText}`,
      );

      const agentMessage: Message = {
        kind: "message",
        role: "agent",
        messageId: uuidv4(),
        parts: [{ kind: "text", text: responseText || "Completed." }],
        taskId: taskId,
        contextId: contextId,
      };

      const finalUpdate: TaskStatusUpdateEvent = {
        kind: "status-update",
        taskId: taskId,
        contextId: contextId,
        status: {
          state: "completed",
          message: agentMessage,
          timestamp: new Date().toISOString(),
        },
        final: true,
      };
      eventBus.publish(finalUpdate);

      console.log(
        `[ContentEditorAgentExecutor] Task ${taskId} finished with state: completed`,
      );
    } catch (error: unknown) {
      console.error(
        `[ContentEditorAgentExecutor] Error processing task ${taskId}:`,
        error,
      );
      const errorMessage =
        error instanceof Error ? error.message : "Unknown error occurred";
      const errorUpdate: TaskStatusUpdateEvent = {
        kind: "status-update",
        taskId: taskId,
        contextId: contextId,
        status: {
          state: "failed",
          message: {
            kind: "message",
            role: "agent",
            messageId: uuidv4(),
            parts: [{ kind: "text", text: `Agent error: ${errorMessage}` }],
            taskId: taskId,
            contextId: contextId,
          },
          timestamp: new Date().toISOString(),
        },
        final: true,
      };
      eventBus.publish(errorUpdate);
    }
  }
}

const contentEditorAgentCard: AgentCard = {
  name: "Content Editor Agent (JS)",
  description: "An agent that can proof-read and polish content.",
  url: "http://localhost:10003/",
  provider: {
    organization: "A2A Samples",
    url: "https://example.com/a2a-samples",
  },
  version: "1.0.0",
  capabilities: {
    streaming: true,
    pushNotifications: false,
    stateTransitionHistory: false,
  },
  securitySchemes: undefined,
  security: undefined,
  defaultInputModes: ["text"],
  defaultOutputModes: ["text"],
  skills: [
    {
      id: "editor",
      name: "Edits content",
      description: "Edits content by proof-reading and polishing",
      tags: ["writer"],
      examples: [
        "Edit the following article, make sure it has a professional tone",
      ],
      inputModes: ["text"],
      outputModes: ["text"],
    },
  ],
  supportsAuthenticatedExtendedCard: false,
};

async function main() {
  const taskStore: TaskStore = new InMemoryTaskStore();
  const agentExecutor: AgentExecutor = new ContentEditorAgentExecutor();
  const requestHandler = new DefaultRequestHandler(
    contentEditorAgentCard,
    taskStore,
    agentExecutor,
  );

  const appBuilder = new A2AExpressApp(requestHandler);
  // Type assertion needed due to Express type compatibility between project and SDK versions
  const expressApp = appBuilder.setupRoutes(express() as any);

  const PORT = process.env.CONTENT_EDITOR_AGENT_PORT || 10003;
  expressApp.listen(PORT, () => {
    console.log(
      `[ContentEditorAgent] Server using new framework started on http://localhost:${PORT}`,
    );
    console.log(
      `[ContentEditorAgent] Agent Card: http://localhost:${PORT}/.well-known/agent-card.json`,
    );
    console.log("[ContentEditorAgent] Press Ctrl+C to stop the server");
  });
}

main().catch(console.error);
