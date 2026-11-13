/* eslint-disable n/no-missing-import */
import express from "express";
import {
    A2A_PROTOCOL_VERSION,
    AGENT_CARD_PATH,
    AgentCard,
    Message,
    Role,
    Task,
    TaskState,
    TaskStatusUpdateEvent,
} from "@a2a-js/sdk";
import {
    AgentEvent,
    AgentExecutor,
    DefaultExecutionEventBusManager,
    DefaultRequestHandler,
    ExecutionEventBus,
    InMemoryTaskStore,
    RequestContext,
    TaskStore,
} from "@a2a-js/sdk/server";
import {
    agentCardHandler,
    jsonRpcHandler,
    UserBuilder,
} from "@a2a-js/sdk/server/express";
import {
    Client,
    ClientFactory,
    ClientFactoryOptions,
    DefaultAgentCardResolver,
    JsonRpcTransportFactory,
} from "@a2a-js/sdk/client";
import * as dotenv from "dotenv";
import {
    IN_TASK_OID4VP_EXTENSION_URI,
    InTaskOpenId4VpExtension,
    InTaskOpenId4VpMessageMetadata,
} from "../extension";
import {
    agentText,
    bindOrExit,
    partsToText,
    statusEvent,
    TERMINAL_TASK_STATES,
    textPart,
    uuid,
} from "../a2a-helpers";

dotenv.config();

const ASSISTANT_A2A_PORT = Number(process.env.ASSISTANT_AGENT_PORT) || 10004;
const MERCHANT_URL = process.env.MERCHANT_AGENT_URL || "http://localhost:10003";

const ASSISTANT_AGENT_CARD: AgentCard = {
    name: "Travel Assistant",
    description:
        "A personal assistant agent that books travel on the user's behalf via partner agents.",
    supportedInterfaces: [
        {
            protocolBinding: "JSONRPC",
            protocolVersion: A2A_PROTOCOL_VERSION,
            url: `http://localhost:${ASSISTANT_A2A_PORT}/`,
            tenant: "",
        },
    ],
    provider: {
        organization: "A2A Samples",
        url: "https://example.com/a2a-samples",
    },
    version: "1.0.0",
    capabilities: {
        streaming: true,
        pushNotifications: false,
        extendedAgentCard: false,
        extensions: [
            {
                uri: IN_TASK_OID4VP_EXTENSION_URI,
                description:
                    "Supports OID4VP In-Task Authorization extension, main purpose is relaying presentation between the user and downstream agents",
                required: false,
                params: { oid4vpVersions: ["1.0"] },
            } satisfies InTaskOpenId4VpExtension,
        ],
    },
    defaultInputModes: ["text"],
    defaultOutputModes: ["text"],
    skills: [
        {
            id: "travel-assistant",
            name: "Book travel on your behalf",
            description:
                "Forwards your booking requests to partner booking agents and relays any authorization back to you.",
            tags: ["assistant", "travel", "delegation"],
            examples: [
                "Book a hotel for Saturday and apply my partner discount",
            ],
            inputModes: ["text"],
            outputModes: ["text"],
            securityRequirements: [],
        },
    ],
    securitySchemes: {},
    securityRequirements: [],
    signatures: [],
};

interface MerchantTaskRef {
    taskId?: string;
    contextId?: string;
}

class AssistantAgentExecutor implements AgentExecutor {
    private readonly cancelledTasks = new Set<string>();
    private merchantClient?: Client;
    private readonly merchantTasks = new Map<string, MerchantTaskRef>();

    public cancelTask = async (taskId: string): Promise<void> => {
        this.cancelledTasks.add(taskId);
    };

    private async getMerchantClient(): Promise<Client> {
        if (!this.merchantClient) {
            const agentCard = await new DefaultAgentCardResolver().resolve(
                MERCHANT_URL
            );
            const factory = new ClientFactory(
                ClientFactoryOptions.createFrom(ClientFactoryOptions.default, {
                    transports: [new JsonRpcTransportFactory()],
                })
            );
            this.merchantClient = await factory.createFromAgentCard(agentCard);
        }
        return this.merchantClient;
    }

    public async execute(
        requestContext: RequestContext,
        eventBus: ExecutionEventBus
    ): Promise<void> {
        const userMessage = requestContext.userMessage;
        const existingTask = requestContext.task;

        const taskId = requestContext.taskId;
        const contextId = requestContext.contextId;
        const userText = partsToText(userMessage.parts).trim();

        console.log(
            `[Assistant] User message ${userMessage.messageId} (task ${taskId}, context ${contextId}): "${userText}"`
        );

        if (!existingTask) {
            const initialTask: Task = {
                id: taskId,
                contextId,
                status: {
                    state: TaskState.TASK_STATE_SUBMITTED,
                    message: undefined,
                    timestamp: new Date().toISOString(),
                },
                artifacts: [],
                history: [userMessage],
                metadata: userMessage.metadata,
            };
            eventBus.publish(AgentEvent.task(initialTask));
        }

        eventBus.publish(
            AgentEvent.statusUpdate(
                statusEvent(
                    taskId,
                    contextId,
                    TaskState.TASK_STATE_WORKING,
                    agentText(
                        taskId,
                        contextId,
                        "Forwarding your request to BlueSky Stays on your behalf..."
                    )
                )
            )
        );

        try {
            await this.forwardAndRelay(userText, taskId, contextId, eventBus);
        } catch (error: unknown) {
            const message =
                error instanceof Error ? error.message : "Unknown error";
            console.error(`[Assistant] Error talking to the merchant:`, error);
            eventBus.publish(
                AgentEvent.statusUpdate(
                    statusEvent(
                        taskId,
                        contextId,
                        TaskState.TASK_STATE_FAILED,
                        agentText(
                            taskId,
                            contextId,
                            `Sorry, I couldn't reach the booking agent: ${message}`
                        )
                    )
                )
            );
        }
    }

    private async forwardAndRelay(
        userText: string,
        taskId: string,
        contextId: string,
        eventBus: ExecutionEventBus
    ): Promise<void> {
        const merchantClient = await this.getMerchantClient();

        const ref = this.merchantTasks.get(contextId) ?? {};
        const forwarded: Message = {
            messageId: uuid(),
            contextId: ref.contextId ?? "",
            taskId: ref.taskId ?? "",
            role: Role.ROLE_USER,
            parts: [textPart(userText)],
            metadata: undefined,
            extensions: [IN_TASK_OID4VP_EXTENSION_URI],
            referenceTaskIds: [],
        };

        for await (const response of merchantClient.sendMessageStream({
            tenant: "",
            message: forwarded,
            configuration: undefined,
            metadata: undefined,
        })) {
            if (this.cancelledTasks.has(taskId)) {
                eventBus.publish(
                    AgentEvent.statusUpdate(
                        statusEvent(
                            taskId,
                            contextId,
                            TaskState.TASK_STATE_CANCELED,
                            undefined
                        )
                    )
                );
                return;
            }

            const payload = response.payload;
            if (!payload) continue;

            if (payload.$case === "task") {
                const merchantTask: Task = payload.value;
                this.merchantTasks.set(contextId, {
                    taskId: merchantTask.id,
                    contextId: merchantTask.contextId,
                });
                continue;
            }

            if (payload.$case === "statusUpdate") {
                const update: TaskStatusUpdateEvent = payload.value;
                const state =
                    update.status?.state ?? TaskState.TASK_STATE_UNSPECIFIED;
                const terminal = TERMINAL_TASK_STATES.has(state);
                this.merchantTasks.set(contextId, {
                    taskId: terminal ? undefined : update.taskId,
                    contextId: update.contextId,
                });

                if (state === TaskState.TASK_STATE_AUTH_REQUIRED) {
                    this.relayAuthRequired(update, taskId, contextId, eventBus);
                    continue;
                }

                eventBus.publish(
                    AgentEvent.statusUpdate(
                        statusEvent(
                            taskId,
                            contextId,
                            state,
                            this.rewriteMessage(
                                update.status?.message,
                                taskId,
                                contextId
                            )
                        )
                    )
                );
            } else if (payload.$case === "message") {
                const message: Message = payload.value;
                if (message.contextId)
                    this.merchantTasks.set(contextId, {
                        taskId: message.taskId,
                        contextId: message.contextId,
                    });
                eventBus.publish(
                    AgentEvent.statusUpdate(
                        statusEvent(
                            taskId,
                            contextId,
                            TaskState.TASK_STATE_WORKING,
                            this.rewriteMessage(message, taskId, contextId)
                        )
                    )
                );
            }
        }
    }

    private relayAuthRequired(
        merchantEvent: TaskStatusUpdateEvent,
        taskId: string,
        contextId: string,
        eventBus: ExecutionEventBus
    ): void {
        const metadata = merchantEvent.status?.message?.metadata?.[
            IN_TASK_OID4VP_EXTENSION_URI
        ] as InTaskOpenId4VpMessageMetadata | undefined;

        if (!metadata?.authorizationRequest) {
            console.warn(
                "[Assistant] auth-required without OID4VP metadata — forwarding the status unchanged."
            );
            eventBus.publish(
                AgentEvent.statusUpdate(
                    statusEvent(
                        taskId,
                        contextId,
                        TaskState.TASK_STATE_AUTH_REQUIRED,
                        this.rewriteMessage(
                            merchantEvent.status?.message,
                            taskId,
                            contextId
                        )
                    )
                )
            );
            return;
        }

        console.log(
            "[Assistant] Merchant requires a credential. I am not the holder of the user's vouchers → relaying upstream."
        );

        eventBus.publish(
            AgentEvent.statusUpdate({
                taskId,
                contextId,
                status: {
                    state: TaskState.TASK_STATE_AUTH_REQUIRED,
                    message: {
                        messageId: uuid(),
                        contextId,
                        taskId,
                        role: Role.ROLE_AGENT,
                        parts: [
                            textPart(
                                "BlueSky Stays needs a partner discount voucher. I don't hold your vouchers, so please present one from your wallet."
                            ),
                        ],
                        metadata: {
                            [IN_TASK_OID4VP_EXTENSION_URI]: {
                                authorizationRequest:
                                    metadata.authorizationRequest,
                            } satisfies InTaskOpenId4VpMessageMetadata,
                        },
                        extensions: [IN_TASK_OID4VP_EXTENSION_URI],
                        referenceTaskIds: [],
                    },
                    timestamp: new Date().toISOString(),
                },
                metadata: undefined,
            })
        );
    }

    private rewriteMessage(
        message: Message | undefined,
        taskId: string,
        contextId: string
    ): Message | undefined {
        if (!message) return undefined;
        return { ...message, taskId, contextId };
    }
}

async function main() {
    const taskStore: TaskStore = new InMemoryTaskStore();
    const agentExecutor = new AssistantAgentExecutor();

    const requestHandler = new DefaultRequestHandler(
        ASSISTANT_AGENT_CARD,
        taskStore,
        agentExecutor,
        new DefaultExecutionEventBusManager()
    );

    const expressApp = express();
    expressApp.use(express.json());
    expressApp.use(
        `/${AGENT_CARD_PATH}`,
        agentCardHandler({ agentCardProvider: requestHandler })
    );
    expressApp.use(
        "/",
        jsonRpcHandler({
            requestHandler,
            userBuilder: UserBuilder.noAuthentication,
        })
    );

    bindOrExit(expressApp, ASSISTANT_A2A_PORT, "Assistant", () => {
        console.log(
            `[Assistant] Travel Assistant A2A server started on http://localhost:${ASSISTANT_A2A_PORT}`
        );
        console.log(
            `[Assistant] Forwarding booking requests to merchant at ${MERCHANT_URL}`
        );
        console.log(
            `[Assistant] Agent Card: http://localhost:${ASSISTANT_A2A_PORT}/.well-known/agent-card.json`
        );
    });
}

main().catch(console.error);
