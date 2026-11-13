/* eslint-disable n/no-missing-import */
import readline from "readline";
import { v4 as uuidv4 } from "uuid";

import { AgentCard, Role, SendMessageRequest } from "@a2a-js/sdk";
import {
    ClientFactory,
    ClientFactoryOptions,
    DefaultAgentCardResolver,
    JsonRpcTransportFactory,
} from "@a2a-js/sdk/client";

const BASE_URL = process.env.AGENT_URL || "http://127.0.0.1:9999";

async function getAgentCard(): Promise<AgentCard> {
    console.log("Initializes the DefaultAgentCardResolver instance");
    // --8<-- [start:A2ACardResolver]
    // Initializes the DefaultAgentCardResolver instance with a base URL
    const resolver = new DefaultAgentCardResolver();
    const publicAgentCard = await resolver.resolve(BASE_URL);
    // --8<-- [end:A2ACardResolver]
    console.log("\nSuccessfully fetched the public agent card:");
    return publicAgentCard;
}

async function showAgentCard(): Promise<void> {
    const publicAgentCard = await getAgentCard();
    console.log(JSON.stringify(publicAgentCard, null, 2));
}

async function sendMessage(textQuery: string = "Hi there"): Promise<void> {
    const publicAgentCard = await getAgentCard();
    console.log("\n--- Public Agent Card - Non-Streaming Call ---");
    // --8<-- [start:message_send]
    console.log("\nInitializing a non-streaming client.");
    const factory = new ClientFactory(
        ClientFactoryOptions.createFrom(ClientFactoryOptions.default, {
            transports: [new JsonRpcTransportFactory()],
        })
    );
    const client = await factory.createFromAgentCard(publicAgentCard);

    const request: SendMessageRequest = {
        tenant: "",
        metadata: {},
        message: {
            messageId: uuidv4(),
            role: Role.ROLE_USER,
            parts: [
                {
                    content: { $case: "text", value: textQuery },
                    metadata: undefined,
                    filename: "",
                    mediaType: "text/plain",
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

    console.log("Response:");
    const response = await client.sendMessage(request);
    console.log(JSON.stringify(response, null, 2));
    // --8<-- [end:message_send]
}

async function sendStreamingMessage(
    textQuery: string = "Hi there"
): Promise<void> {
    const publicAgentCard = await getAgentCard();

    console.log("\n--- Public Agent Card - Streaming Call ---");
    // --8<-- [start:message_stream]
    console.log("\nInitializing a streaming client.");
    const factory = new ClientFactory(
        ClientFactoryOptions.createFrom(ClientFactoryOptions.default, {
            transports: [new JsonRpcTransportFactory()],
        })
    );
    const client = await factory.createFromAgentCard(publicAgentCard);

    const request: SendMessageRequest = {
        tenant: "",
        metadata: {},
        message: {
            messageId: uuidv4(),
            role: Role.ROLE_USER,
            parts: [
                {
                    content: { $case: "text", value: textQuery },
                    metadata: undefined,
                    filename: "",
                    mediaType: "text/plain",
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

    console.log("Response:");
    const stream = client.sendMessageStream(request);
    for await (const chunk of stream) {
        console.log(JSON.stringify(chunk, null, 2));
    }
    // --8<-- [end:message_stream]
}

async function showExtendedCard(): Promise<void> {
    const publicAgentCard = await getAgentCard();
    const factory = new ClientFactory(
        ClientFactoryOptions.createFrom(ClientFactoryOptions.default, {
            transports: [new JsonRpcTransportFactory()],
        })
    );
    const client = await factory.createFromAgentCard(publicAgentCard);

    console.log("\n--- Extended Agent Card - Non-Streaming Call ---");
    const extendedCard = await client.getAgentCard();
    console.log(
        "\nSuccessfully fetched the authenticated extended agent card:"
    );
    console.log(JSON.stringify(extendedCard, null, 2));
}

export async function testClientWorkflow(
    textQuery: string = "Hi there!"
): Promise<void> {
    /**
     * This test function is intended to be used to test the client workflow
     * for multiple queries
     */
    await showAgentCard();
    await sendMessage(textQuery);
    await sendStreamingMessage(textQuery);
    await showExtendedCard();
}

async function main(): Promise<void> {
    console.log(
        `\nStarting an interactive session with A2A Server [${BASE_URL}]`
    );
    console.log("Use `exit` to quit.");

    const rl = readline.createInterface({
        input: process.stdin,
        output: process.stdout,
    });

    const promptUser = () => {
        rl.question("user > ", async (input) => {
            const trimmed = input.trim();
            if (!trimmed || trimmed === "exit") {
                rl.close();
                return;
            }
            try {
                await sendMessage(trimmed);
            } catch (err) {
                console.error("Error sending message:", err);
            }
            promptUser();
        });
    };

    promptUser();
}

if (process.argv[1]?.endsWith("test_client.ts")) {
    main().catch(console.error);
}
