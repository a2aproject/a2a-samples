/* eslint-disable n/no-missing-import */
import express, { Express } from "express";
import {
    A2A_PROTOCOL_VERSION,
    AGENT_CARD_PATH,
    AgentCard,
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

import * as dotenv from "dotenv";
import { createCredoAgent, CredoAgentWithOpenId4Vc } from "../credo-helpers";
import {
    agentText,
    bindOrExit,
    partsToText,
    requireEnv,
    statusEvent,
    textPart,
    uuid,
} from "../a2a-helpers";
import {
    OpenId4VcVerificationSessionRepository,
    OpenId4VcVerificationSessionState,
    OpenId4VcVerificationSessionStateChangedEvent,
    OpenId4VcVerifierEvents,
    OpenId4VcVerifierRecord,
} from "@credo-ts/openid4vc";
import {
    IN_TASK_OID4VP_EXTENSION_URI,
    InTaskOpenId4VpAuthorizationRequest,
    InTaskOpenId4VpExtension,
    InTaskOpenId4VpMessageMetadata,
} from "../extension";
import {
    AppliedDiscount,
    AuthResult,
    evaluateVoucherClaims,
    VOUCHER_DCQL_QUERY,
    VOUCHER_DCQL_QUERY_ID,
} from "./voucher-verification";
import {
    Booking,
    computeSubtotal,
    describeStay,
    parseRequest,
} from "./booking";

dotenv.config();

requireEnv("OPENAI_API_KEY");

const MERCHANT_A2A_PORT = Number(process.env.MERCHANT_AGENT_PORT) || 10003;
const MERCHANT_VERIFIER_PORT =
    Number(process.env.MERCHANT_VERIFIER_PORT) || 3001;

/** How long the merchant waits for a voucher presentation before quoting without a discount. */
const AUTH_TIMEOUT_MS = Number(process.env.MERCHANT_AUTH_TIMEOUT_MS) || 120000;

const usd = (n: number) => `$${n.toFixed(2)}`;

const MERCHANT_AGENT_CARD: AgentCard = {
    name: "BlueSky Stays",
    description:
        "A hotel-booking agent that honors discount vouchers issued by partner travel brands.",
    supportedInterfaces: [
        {
            protocolBinding: "JSONRPC",
            protocolVersion: A2A_PROTOCOL_VERSION,
            url: `http://localhost:${MERCHANT_A2A_PORT}/`,
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
                    "Provides an option to use OpenID for Verifiable Presentations (OID4VP) for In-Task Authorization",
                required: false,
                params: { oid4vpVersions: ["1.0"] },
            } satisfies InTaskOpenId4VpExtension,
        ],
    },
    defaultInputModes: ["text"],
    defaultOutputModes: ["text"],
    skills: [
        {
            id: "booking",
            name: "Hotel booking with partner discounts",
            description:
                "Quotes hotel stays and applies partner discount vouchers (presented via OID4VP) issued by trusted travel brands.",
            tags: ["booking", "travel", "discount"],
            examples: [
                "Book the Grand Hotel for Saturday",
                "Book a stay and apply my partner discount",
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

class MerchantAgentExecutor implements AgentExecutor {
    private readonly cancelledTasks = new Set<string>();

    private readonly authResults = new Map<string, AuthResult>();
    private readonly authWaiters = new Map<
        string,
        (result: AuthResult) => void
    >();

    private readonly credoExpressApp: Express = express();
    private readonly credoAgent: CredoAgentWithOpenId4Vc;

    constructor() {
        this.credoAgent = createCredoAgent("bluesky-merchant", {
            app: this.credoExpressApp,
            port: MERCHANT_VERIFIER_PORT,
        });
    }

    public async initialize(): Promise<void> {
        await this.credoAgent.initialize();

        this.credoAgent.events.on(
            OpenId4VcVerifierEvents.VerificationSessionStateChanged,
            this.onVerificationStateChanged.bind(this)
        );

        // A stale process on this port would silently serve the wrong verifier and 404 every VP.
        bindOrExit(
            this.credoExpressApp,
            MERCHANT_VERIFIER_PORT,
            "Merchant",
            () => {
                console.log(
                    `[Merchant] OID4VP verifier listening on http://localhost:${MERCHANT_VERIFIER_PORT}/oid4vp`
                );
            }
        );
    }

    public cancelTask = async (taskId: string): Promise<void> => {
        this.cancelledTasks.add(taskId);
    };

    public async execute(
        requestContext: RequestContext,
        eventBus: ExecutionEventBus
    ): Promise<void> {
        const userMessage = requestContext.userMessage;
        const existingTask = requestContext.task;

        const taskId = requestContext.taskId;
        const contextId = requestContext.contextId;

        console.log(
            `[Merchant] Processing message ${userMessage.messageId} for task ${taskId} (context: ${contextId})`
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

        const userText = partsToText(userMessage.parts).trim();

        let discount: AppliedDiscount | undefined;
        let rejectionReason: string | undefined;

        this.publishWorking(
            taskId,
            contextId,
            eventBus,
            "Reviewing your booking request..."
        );
        const booking = await parseRequest(userText);

        // JIT authorization: every discount request triggers a fresh voucher presentation (no caching), so the flow is repeatable within a session.
        if (booking.wantsPartnerDiscount) {
            try {
                const result = await this.requestAndAwaitVoucher(
                    contextId,
                    taskId,
                    eventBus
                );
                if (result.approved && result.discount) {
                    discount = result.discount;
                } else {
                    rejectionReason =
                        result.reason ?? "the voucher could not be accepted";
                }
            } catch (err) {
                rejectionReason =
                    err instanceof Error
                        ? err.message
                        : "authorization did not complete";
            }
        }

        this.publishWorking(
            taskId,
            contextId,
            eventBus,
            "Preparing your quote..."
        );

        const subtotal = computeSubtotal(booking);
        const finalPrice = discount
            ? Math.round(subtotal * (1 - discount.percentOff / 100))
            : subtotal;
        const quoteLine = this.buildQuoteLine(
            booking,
            discount,
            rejectionReason,
            subtotal,
            finalPrice
        );
        console.log(`[Merchant] ${quoteLine}`);

        try {
            // The quote line is authoritative and deterministic (the LLM is used only to
            // parse/understand the request).
            const replyText = quoteLine;

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

            eventBus.publish(
                AgentEvent.statusUpdate(
                    statusEvent(
                        taskId,
                        contextId,
                        TaskState.TASK_STATE_COMPLETED,
                        agentText(taskId, contextId, replyText)
                    )
                )
            );
            console.log(
                `[Merchant] Task ${taskId} finished with state: completed`
            );
        } catch (error: unknown) {
            console.error(`[Merchant] Error processing task ${taskId}:`, error);
            const errorMessage =
                error instanceof Error
                    ? error.message
                    : "Unknown error occurred";
            eventBus.publish(
                AgentEvent.statusUpdate(
                    statusEvent(
                        taskId,
                        contextId,
                        TaskState.TASK_STATE_FAILED,
                        agentText(
                            taskId,
                            contextId,
                            `Agent error: ${errorMessage}`
                        )
                    )
                )
            );
        }
    }

    private buildQuoteLine(
        booking: Booking,
        discount: AppliedDiscount | undefined,
        rejectionReason: string | undefined,
        subtotal: number,
        finalPrice: number
    ): string {
        const stay = describeStay(booking);
        if (discount) {
            const brand = discount.brand ?? "partner";
            return (
                `Quote for ${stay}: ${usd(subtotal)}, with your ${brand} partner ` +
                `discount (${discount.percentOff}% off) applied -> final price ${usd(finalPrice)}.`
            );
        }
        if (rejectionReason) {
            return `We couldn't apply the requested partner discount (${rejectionReason}). Quote for ${stay}: ${usd(subtotal)}.`;
        }
        return `Quote for ${stay}: ${usd(subtotal)}.`;
    }

    private async requestAndAwaitVoucher(
        contextId: string,
        taskId: string,
        eventBus: ExecutionEventBus
    ): Promise<AuthResult> {
        // Drop any stale outcome so a retry within the same context waits for a fresh presentation.
        this.authResults.delete(contextId);

        const authorizationRequest =
            await this.createAuthorizationRequestForContext(contextId);

        const authRequired: TaskStatusUpdateEvent = {
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
                            "Please present a partner discount voucher to apply your discount."
                        ),
                    ],
                    metadata: {
                        [IN_TASK_OID4VP_EXTENSION_URI]: {
                            authorizationRequest,
                        } satisfies InTaskOpenId4VpMessageMetadata,
                    },
                    extensions: [IN_TASK_OID4VP_EXTENSION_URI],
                    referenceTaskIds: [],
                },
                timestamp: new Date().toISOString(),
            },
            metadata: undefined,
        };
        eventBus.publish(AgentEvent.statusUpdate(authRequired));

        return this.waitForAuthResult(contextId);
    }

    private async createAuthorizationRequestForContext(
        contextId: string
    ): Promise<InTaskOpenId4VpAuthorizationRequest> {
        const verificationSessionRepository =
            this.credoAgent.dependencyManager.resolve(
                OpenId4VcVerificationSessionRepository
            );
        const { verifierId } = await this.getOrCreateVerifierRecord();

        const {
            authorizationRequest: request_uri,
            authorizationRequestObject: request,
            verificationSession,
        } = await this.credoAgent.openid4vc.verifier.createAuthorizationRequest(
            {
                verifierId,
                responseMode: "direct_post",
                requestSigner: { method: "none" },
                dcql: { query: VOUCHER_DCQL_QUERY },
                version: "v1",
            }
        );

        verificationSession.setTag("contextId", contextId);
        await verificationSessionRepository.update(
            this.credoAgent.context,
            verificationSession
        );

        return { request_uri, client_id: request.client_id };
    }

    private async getOrCreateVerifierRecord(): Promise<OpenId4VcVerifierRecord> {
        const records =
            await this.credoAgent.openid4vc.verifier.getAllVerifiers();
        return records.length > 0
            ? records[0]
            : await this.credoAgent.openid4vc.verifier.createVerifier();
    }

    private async onVerificationStateChanged(
        event: OpenId4VcVerificationSessionStateChangedEvent
    ): Promise<void> {
        const { verificationSession } = event.payload;
        if (
            verificationSession.state !==
            OpenId4VcVerificationSessionState.ResponseVerified
        )
            return;

        const contextId = verificationSession.getTag("contextId") as
            string | undefined;
        if (!contextId) return;

        const result = await this.evaluatePresentation(verificationSession.id);
        this.authResults.set(contextId, result);

        const waiter = this.authWaiters.get(contextId);
        if (waiter) {
            this.authWaiters.delete(contextId);
            waiter(result);
        }
    }

    private async evaluatePresentation(
        verificationSessionId: string
    ): Promise<AuthResult> {
        try {
            const verified =
                await this.credoAgent.openid4vc.verifier.getVerifiedAuthorizationResponse(
                    verificationSessionId
                );
            const presentation =
                verified.dcql?.presentations?.[VOUCHER_DCQL_QUERY_ID]?.[0];

            if (!presentation || !("prettyClaims" in presentation)) {
                return {
                    approved: false,
                    reason: "no discount voucher was presented",
                };
            }

            const claims = (
                presentation as { prettyClaims: Record<string, unknown> }
            ).prettyClaims;
            return evaluateVoucherClaims(claims);
        } catch (error) {
            console.error(
                "[Merchant] Failed to evaluate voucher presentation:",
                error
            );
            return {
                approved: false,
                reason:
                    error instanceof Error
                        ? error.message
                        : "the voucher could not be verified",
            };
        }
    }

    private waitForAuthResult(
        contextId: string,
        timeoutMs = AUTH_TIMEOUT_MS
    ): Promise<AuthResult> {
        const existing = this.authResults.get(contextId);
        if (existing) return Promise.resolve(existing);

        return new Promise<AuthResult>((resolve, reject) => {
            const waiter = (result: AuthResult) => {
                clearTimeout(timer);
                resolve(result);
            };
            const timer = setTimeout(() => {
                // Only clear our own waiter — a newer request for this context may have replaced it.
                if (this.authWaiters.get(contextId) === waiter)
                    this.authWaiters.delete(contextId);
                reject(new Error("authorization timed out"));
            }, timeoutMs);
            this.authWaiters.set(contextId, waiter);
        });
    }

    private publishWorking(
        taskId: string,
        contextId: string,
        eventBus: ExecutionEventBus,
        text: string
    ): void {
        eventBus.publish(
            AgentEvent.statusUpdate(
                statusEvent(
                    taskId,
                    contextId,
                    TaskState.TASK_STATE_WORKING,
                    agentText(taskId, contextId, text)
                )
            )
        );
    }
}

async function main() {
    const taskStore: TaskStore = new InMemoryTaskStore();
    const agentExecutor = new MerchantAgentExecutor();

    await agentExecutor.initialize();

    const requestHandler = new DefaultRequestHandler(
        MERCHANT_AGENT_CARD,
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

    bindOrExit(expressApp, MERCHANT_A2A_PORT, "Merchant", () => {
        console.log(
            `[Merchant] BlueSky Stays A2A server started on http://localhost:${MERCHANT_A2A_PORT}`
        );
        console.log(
            `[Merchant] Agent Card: http://localhost:${MERCHANT_A2A_PORT}/.well-known/agent-card.json`
        );
        console.log("[Merchant] Press Ctrl+C to stop the server");
    });
}

main().catch(console.error);
