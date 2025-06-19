import { v4 as uuidv4 } from 'uuid'; // For generating unique IDs
import { ElizaBot } from "@agentic-profile/eliza";
import { ClientAgentSession } from '@agentic-profile/auth';

import {
    AgentExecutor,
    RequestContext,
    ExecutionEventBus,
    TaskStatusUpdateEvent,
    TextPart,
    Message
} from "@a2a-js/sdk";
import { SessionContextStore } from "./store.js";

/**
 * ElizaAgentExecutor implements the Eliza DOCTOR agent.
 */
export class ElizaAgentExecutor implements AgentExecutor {
    private sessionContextStore: SessionContextStore;

    constructor( sessionContextStore: SessionContextStore ) {
        this.sessionContextStore = sessionContextStore;
    }

    public cancelTask = async (
        _taskId: string,
        _eventBus: ExecutionEventBus,
    ): Promise<void> => {
        console.log( `[ElizaAgentExecutor] Does not support Cancelling tasks` );
    };

    async execute(
        requestContext: RequestContext,
        eventBus: ExecutionEventBus
    ): Promise<void> {
        const userMessage = requestContext.userMessage;
        const taskId = requestContext.taskId;
        const contextId = requestContext.contextId;
        const sessionId = getSessionId( requestContext );
        console.log(
            `[ElizaAgentExecutor] Processing message ${userMessage.messageId} for task ${taskId} context ${contextId} in session ${sessionId ?? "- none -"}`
        );

        try {
            const userText = userMessage.parts
                .filter((p) => p.kind === 'text' && !!p.text)
                .map(p => (p as TextPart).text)
                .join('. ');

            const eliza = new ElizaBot(false);
            const elizaState = await this.sessionContextStore.loadContext( sessionId, contextId );
            if( elizaState )
                eliza.setState( elizaState );
        
            const agentReplyText = userText ? eliza.transform( userText )!: eliza.getInitial()!;
        
            await this.sessionContextStore.saveContext( sessionId, contextId, eliza.getState() );

            // 5. Publish final task status update
            const agentMessage: Message = {
                kind: 'message',
                role: 'agent',
                messageId: uuidv4(),
                parts: [{ kind: 'text', text: agentReplyText }], // Ensure some text
                taskId: undefined, // Don't pass taskId to client, otherwise it will be passed back to the server in the next request
                contextId: contextId,
            };
            eventBus.publish(agentMessage);

            console.log(
                `[ElizaAgentExecutor] Context ${contextId} finished`
            );

        } catch (error: any) {
            console.error(
            `[ElizaAgentExecutor] Error processing task ${taskId}:`,
            error
            );
            const errorUpdate: TaskStatusUpdateEvent = {
                kind: 'status-update',
                taskId: taskId,
                contextId: contextId,
                status: {
                    state: 'failed',
                    message: {
                        kind: 'message',
                        role: 'agent',
                        messageId: uuidv4(),
                        parts: [{ kind: 'text', text: `Agent error: ${error.message}` }],
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

function getSessionId( requestContext: RequestContext ): string {
    const session = (requestContext as any)?.session as ClientAgentSession;
    return session?.agentDid ?? "";
}
