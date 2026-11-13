/* eslint-disable n/no-missing-import, n/no-process-exit */

import readline from "node:readline";

import {
    Message,
    Part,
    Role,
    SendMessageRequest,
    Task,
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatusUpdateEvent,
    taskStateToJSON,
} from "@a2a-js/sdk";
import {
    Client,
    ClientFactory,
    ClientFactoryOptions,
    DefaultAgentCardResolver,
    JsonRpcTransportFactory,
} from "@a2a-js/sdk/client";
import * as dotenv from "dotenv";
import { createCredoAgent, CredoAgentWithOpenId4Vc } from "./credo-helpers";
import { provisionVouchers } from "./vouchers";
import {
    IN_TASK_OID4VP_EXTENSION_URI,
    InTaskOpenId4VpMessageMetadata,
} from "./extension";
import {
    presentVoucher,
    PresentationOutcome,
    VoucherOption,
} from "./holder-wallet";
import { TERMINAL_TASK_STATES, textPart, uuid } from "./a2a-helpers";

dotenv.config();

// ANSI colors
const colors = {
    reset: "\x1b[0m",
    bright: "\x1b[1m",
    dim: "\x1b[2m",
    red: "\x1b[31m",
    green: "\x1b[32m",
    yellow: "\x1b[33m",
    blue: "\x1b[34m",
    magenta: "\x1b[35m",
    cyan: "\x1b[36m",
    gray: "\x1b[90m",
};

function colorize(color: keyof typeof colors, text: string): string {
    return `${colors[color]}${text}${colors.reset}`;
}

const serverUrl =
    process.argv[2] ||
    process.env.ASSISTANT_AGENT_URL ||
    "http://localhost:10004";
let client: Client;
let agentName = "Agent";
let currentTaskId: string | undefined;
let currentContextId: string | undefined;

async function createClient(): Promise<Client> {
    const agentCard = await new DefaultAgentCardResolver().resolve(serverUrl);
    agentName = agentCard.name || agentName;
    const factory = new ClientFactory(
        ClientFactoryOptions.createFrom(ClientFactoryOptions.default, {
            transports: [new JsonRpcTransportFactory()],
        })
    );
    return factory.createFromAgentCard(agentCard);
}

const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
});

function question(prompt: string): Promise<string> {
    return new Promise((resolve) => rl.question(prompt, resolve));
}

function printMessageContent(message: Message) {
    message.parts.forEach((part: Part, index: number) => {
        const prefix = colorize("red", `  Part ${index + 1}:`);
        switch (part.content?.$case) {
            case "text":
                console.log(
                    `${prefix} ${colorize("green", "📝 Text:")} ${part.content.value}`
                );
                break;
            case "data":
                console.log(
                    `${prefix} ${colorize("yellow", "📊 Data:")}`,
                    JSON.stringify(part.content.value)
                );
                break;
            case "raw":
            case "url":
                console.log(`${prefix} ${colorize("blue", "📄 File")}`);
                break;
        }
    });
}

const STATE_EMOJI: Partial<Record<TaskState, string>> = {
    [TaskState.TASK_STATE_WORKING]: "⏳",
    [TaskState.TASK_STATE_INPUT_REQUIRED]: "🤔",
    [TaskState.TASK_STATE_AUTH_REQUIRED]: "🔐",
    [TaskState.TASK_STATE_COMPLETED]: "✅",
    [TaskState.TASK_STATE_CANCELED]: "⏹️",
    [TaskState.TASK_STATE_FAILED]: "❌",
};

/** Renders `TASK_STATE_AUTH_REQUIRED` as `auth-required` for readability. */
function stateLabel(state: TaskState): string {
    return taskStateToJSON(state)
        .replace(/^TASK_STATE_/, "")
        .toLowerCase()
        .replace(/_/g, "-");
}

function printStatusUpdate(event: TaskStatusUpdateEvent) {
    const ts = new Date().toLocaleTimeString();
    const prefix = colorize("magenta", `\n${agentName} [${ts}]:`);
    const state = event.status?.state ?? TaskState.TASK_STATE_UNSPECIFIED;
    const emoji = STATE_EMOJI[state] ?? "ℹ️";
    const isFinal = TERMINAL_TASK_STATES.has(state);
    console.log(
        `${prefix} ${emoji} Status: ${colorize("cyan", stateLabel(state))} ${isFinal ? colorize("bright", "[FINAL]") : ""}`
    );
    if (event.status?.message) printMessageContent(event.status.message);
}

function printArtifactUpdate(event: TaskArtifactUpdateEvent) {
    const ts = new Date().toLocaleTimeString();
    const prefix = colorize("magenta", `\n${agentName} [${ts}]:`);
    console.log(
        `${prefix} 📄 Artifact: ${event.artifact?.name || "(unnamed)"}`
    );
    printMessageContent({
        messageId: uuid(),
        contextId: event.contextId,
        taskId: event.taskId,
        role: Role.ROLE_AGENT,
        parts: event.artifact?.parts ?? [],
        metadata: undefined,
        extensions: [],
        referenceTaskIds: [],
    });
}

async function handleAuthRequest(
    credoAgent: CredoAgentWithOpenId4Vc,
    requestUri: string
): Promise<PresentationOutcome["status"]> {
    const outcome = await presentVoucher(credoAgent, requestUri, {
        choose: async (options: VoucherOption[], purpose) => {
            console.log(
                colorize(
                    "green",
                    `\n🔐 The agent requested a verifiable credential${purpose ? ` (purpose: "${purpose}")` : ""}.`
                )
            );
            // Stable, readable order (the wallet's underlying match order is not guaranteed).
            const sorted = [...options].sort((a, b) =>
                String(a.claims.issuer_brand ?? a.claims.iss).localeCompare(
                    String(b.claims.issuer_brand ?? b.claims.iss)
                )
            );
            console.log(
                colorize(
                    "dim",
                    `Your wallet holds ${sorted.length} matching credential(s):`
                )
            );
            sorted.forEach((o, i) => {
                const c = o.claims;
                console.log(
                    `  ${colorize("bright", `[${i + 1}]`)} ${c.issuer_brand ?? c.iss} — ${c.percent_off}% off, expires ${c.expires_at}`
                );
            });
            const answer = (
                await question(
                    colorize(
                        "cyan",
                        `Choose a voucher to present (1-${sorted.length}), or 'n' to decline: `
                    )
                )
            ).trim();
            const choice = Number(answer);
            if (
                !Number.isInteger(choice) ||
                choice < 1 ||
                choice > sorted.length
            )
                return null;
            return sorted[choice - 1];
        },
        confirm: async (requestedClaims) => {
            console.log(
                colorize(
                    "yellow",
                    `\nPresenting will disclose ONLY: ${JSON.stringify(requestedClaims)}`
                )
            );
            console.log(
                colorize(
                    "dim",
                    `(Your identity, voucher id and issuing brand stay private.)`
                )
            );
            const confirm = (
                await question(colorize("cyan", "Confirm sharing? (yes/no): "))
            )
                .trim()
                .toLowerCase();
            return confirm === "yes" || confirm === "y";
        },
    });

    switch (outcome.status) {
        case "sent":
            console.log(
                colorize("green", "✓ Presentation sent to the verifier.")
            );
            break;
        case "unsatisfiable":
            console.log(
                colorize(
                    "red",
                    "Your wallet has no credential that satisfies this request."
                )
            );
            break;
        case "declined":
            console.log(
                colorize(
                    "red",
                    "Authorization cancelled — unable to proceed with the task."
                )
            );
            break;
        case "failed":
            console.log(
                colorize("red", "Failed to submit the presentation."),
                outcome.detail
            );
            break;
    }
    return outcome.status;
}

async function createAndProvisionWallet(): Promise<CredoAgentWithOpenId4Vc> {
    // Holder-only Credo agent: it makes outbound OID4VP calls to the merchant's verifier and serves
    // no endpoints of its own, so it needs no express app or port.
    const credoAgent = createCredoAgent("a2a-client");
    await credoAgent.initialize();

    const vouchers = await provisionVouchers(credoAgent);

    console.log(
        colorize(
            "green",
            `\n👛 Wallet provisioned with ${vouchers.length} discount voucher(s):`
        )
    );
    for (const v of vouchers) {
        console.log(
            colorize(
                "dim",
                `   • ${v.brand}: ${v.percentOff}% off (expires ${v.expiresAt})`
            )
        );
    }

    return credoAgent;
}

async function sendMessage(
    credoAgent: CredoAgentWithOpenId4Vc,
    text: string
): Promise<void> {
    const message: Message = {
        messageId: uuid(),
        contextId: currentContextId ?? "",
        taskId: currentTaskId ?? "",
        role: Role.ROLE_USER,
        parts: [textPart(text)],
        metadata: undefined,
        extensions: [IN_TASK_OID4VP_EXTENSION_URI],
        referenceTaskIds: [],
    };

    const params: SendMessageRequest = {
        tenant: "",
        message,
        configuration: undefined,
        metadata: undefined,
    };

    console.log(colorize("red", "Sending message..."));
    const stream = client.sendMessageStream(params);

    for await (const response of stream) {
        const payload = response.payload;
        if (!payload) continue;

        if (payload.$case === "statusUpdate") {
            const statusEvent = payload.value;
            printStatusUpdate(statusEvent);

            const state =
                statusEvent.status?.state ?? TaskState.TASK_STATE_UNSPECIFIED;

            if (state === TaskState.TASK_STATE_AUTH_REQUIRED) {
                const metadata = statusEvent.status?.message?.metadata?.[
                    IN_TASK_OID4VP_EXTENSION_URI
                ] as InTaskOpenId4VpMessageMetadata | undefined;
                if (!metadata?.authorizationRequest) {
                    console.log(
                        colorize(
                            "yellow",
                            "Received 'auth-required' without OID4VP metadata. Skipping."
                        )
                    );
                    continue;
                }
                const outcome = await handleAuthRequest(
                    credoAgent,
                    metadata.authorizationRequest.request_uri
                );
                if (outcome !== "sent") {
                    // We won't present a credential. The merchant cannot be told out-of-band that we declined,
                    // so it will move on only after its own auth timeout.
                    // We abandon this turn and reset to a clean task + context so the next message starts fresh.
                    currentTaskId = undefined;
                    currentContextId = undefined;
                    console.log(
                        colorize(
                            "dim",
                            "--- Authorization not completed; returning to the prompt. ---"
                        )
                    );
                    return;
                }
            }
            if (TERMINAL_TASK_STATES.has(state)) {
                currentTaskId = undefined;
            }
        } else if (payload.$case === "artifactUpdate") {
            printArtifactUpdate(payload.value);
        } else if (payload.$case === "task") {
            const task: Task = payload.value;
            currentTaskId = task.id;
            currentContextId = task.contextId;
        } else if (payload.$case === "message") {
            const message: Message = payload.value;
            if (message.taskId) currentTaskId = message.taskId;
            if (message.contextId) currentContextId = message.contextId;
            printMessageContent(message);
        }
    }
    console.log(colorize("dim", `--- End of response stream ---`));
}

async function main() {
    console.log(
        colorize("bright", "A2A Terminal Client (OID4VP In-Task Auth demo)")
    );
    console.log(colorize("dim", `Connecting to: ${serverUrl}`));

    const credoAgent = await createAndProvisionWallet();

    try {
        client = await createClient();
        console.log(colorize("green", `✓ Connected to "${agentName}".`));
    } catch (error) {
        const detail = error instanceof Error ? error.message : error;
        console.log(
            colorize(
                "yellow",
                `⚠️ Could not connect to ${serverUrl} (is the agent running?): ${detail}`
            )
        );
        await credoAgent.shutdown();
        process.exit(1);
    }

    console.log(
        colorize(
            "green",
            `Type a message. Use '/new' to reset the session, '/exit' to quit.`
        )
    );

    for (;;) {
        const input = (
            await question(colorize("cyan", `\n${agentName} > You: `))
        ).trim();
        if (!input) continue;
        if (input.toLowerCase() === "/exit") break;
        if (input.toLowerCase() === "/new") {
            currentTaskId = undefined;
            currentContextId = undefined;
            console.log(
                colorize("bright", "✨ New session — task and context cleared.")
            );
            continue;
        }
        try {
            await sendMessage(credoAgent, input);
        } catch (error) {
            const message = error instanceof Error ? error.message : error;
            console.error(colorize("red", `Error: ${message}`));
        }
    }

    rl.close();
    await credoAgent.shutdown();
    console.log(colorize("yellow", "Goodbye!"));
    process.exit(0);
}

main().catch((err) => {
    console.error(colorize("red", "Unhandled error in main:"), err);
    process.exit(1);
});
