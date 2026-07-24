/* eslint-disable n/no-missing-import */
import {
    AgentCard,
    Artifact,
    Message,
    Role,
    SendMessageRequest,
    TaskState,
} from "@a2a-js/sdk";
import {
    ClientFactory,
    DefaultAgentCardResolver,
    JsonRpcTransportFactory,
} from "@a2a-js/sdk/client";
import { v4 as uuidv4 } from "uuid";

import {
    wrapClientFactory,
    TIMESTAMP_FIELD,
    TimestampExtension,
} from "./timestamp_ext/index.js";

const AGENT_URL = process.env.AGENT_URL || "http://127.0.0.1:9998";
const TIMESTAMP_UNIX = 1700000000.0;

async function getAgentCard(): Promise<AgentCard> {
    const resolver = new DefaultAgentCardResolver();
    const card = await resolver.resolve(AGENT_URL);
    return card;
}

async function main(): Promise<void> {
    const expectedIso = new Date(TIMESTAMP_UNIX * 1000).toISOString();
    // Initialize with TIMESTAMP_UNIX for validation
    const ext = new TimestampExtension(() => TIMESTAMP_UNIX);

    console.log(`Resolving agent card from ${AGENT_URL}...`);
    const card = await getAgentCard();

    console.log("Creating client factory and client...");
    const baseFactory = new ClientFactory({
        transports: [new JsonRpcTransportFactory()],
    });
    const factory = wrapClientFactory(baseFactory, ext);
    const client = await factory.createFromAgentCard(card);

    const request: SendMessageRequest = {
        tenant: "",
        metadata: {},
        message: {
            messageId: uuidv4(),
            role: Role.ROLE_USER,
            parts: [
                {
                    content: { $case: "text", value: "hi" },
                    mediaType: "text/plain",
                    filename: "",
                    metadata: {},
                },
            ],
            taskId: "",
            contextId: "",
            extensions: [],
            metadata: {},
            referenceTaskIds: [],
        },
        configuration: undefined,
    };

    console.log("\n--- streaming response from the agent ---");
    const stream = client.sendMessageStream(request);

    const artifacts: Artifact[] = [];
    const statusMessages: Message[] = [];

    for await (const chunk of stream) {
        if (chunk.payload?.$case === "artifactUpdate") {
            const art = chunk.payload.value.artifact;
            if (art) {
                artifacts.push(art);
                const timestamp = art.metadata?.[TIMESTAMP_FIELD];
                console.log(`  artifact "${art.name}" @ ${timestamp}`);
            }
        } else if (chunk.payload?.$case === "statusUpdate") {
            const status = chunk.payload.value.status;
            if (status) {
                const stateName = TaskState[status.state];
                if (status.message) {
                    statusMessages.push(status.message);
                    const timestamp =
                        status.message.metadata?.[TIMESTAMP_FIELD];
                    console.log(`  status=${stateName} message @ ${timestamp}`);
                } else {
                    console.log(`  status=${stateName}`);
                }
            }
        } else {
            console.log(`  event of kind ${chunk.payload?.$case}`);
        }
    }

    // Assertions / Verification
    console.log("\nVerifying timestamps...");
    if (artifacts.length === 0) {
        throw new Error("Verification failed: Agent did not emit an artifact");
    }
    if (statusMessages.length === 0) {
        throw new Error(
            "Verification failed: Agent did not emit a status message"
        );
    }

    for (const art of artifacts) {
        const ts = art.metadata?.[TIMESTAMP_FIELD];
        if (ts !== expectedIso) {
            throw new Error(
                `Verification failed: Expected artifact timestamp ${expectedIso}, got ${ts}`
            );
        }
    }
    for (const msg of statusMessages) {
        const ts = msg.metadata?.[TIMESTAMP_FIELD];
        if (ts !== expectedIso) {
            throw new Error(
                `Verification failed: Expected message timestamp ${expectedIso}, got ${ts}`
            );
        }
    }

    console.log("Verification successful! All timestamps match.");
}

main().catch((err) => {
    console.error("Error running test client:", err);
    // eslint-disable-next-line n/no-process-exit
    process.exit(1);
});
