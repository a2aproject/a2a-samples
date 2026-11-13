/* eslint-disable n/no-missing-import */
import { AgentCard, SendMessageRequest } from "@a2a-js/sdk";
import {
    BeforeArgs,
    CallInterceptor,
    Client,
    ClientFactory,
    ClientFactoryOptions,
    ServiceParameters,
    withA2AExtensions,
} from "@a2a-js/sdk/client";
import { TimestampExtension, URI } from "./core.js";

export function wrapClientFactory(
    factory: ClientFactory,
    ext: TimestampExtension
): ClientFactory {
    return new TimestampingClientFactory(factory, ext);
}

export function clientInterceptor(ext: TimestampExtension): CallInterceptor {
    return new TimestampingClientInterceptor(ext);
}

class TimestampingClientFactory extends ClientFactory {
    private readonly factoryWithInterceptor: ClientFactory;

    constructor(
        delegate: ClientFactory,
        private readonly ext: TimestampExtension
    ) {
        const newOptions = ClientFactoryOptions.createFrom(delegate.options, {
            clientConfig: {
                interceptors: [clientInterceptor(ext)],
            },
        });
        super(newOptions);
        this.factoryWithInterceptor = new ClientFactory(newOptions);
    }

    override async createFromAgentCard(agentCard: AgentCard): Promise<Client> {
        return this.factoryWithInterceptor.createFromAgentCard(agentCard);
    }
}

class TimestampingClientInterceptor implements CallInterceptor {
    constructor(private readonly ext: TimestampExtension) {}

    async before(args: BeforeArgs): Promise<void> {
        if (!args.input) {
            return;
        }
        const method = args.input.method;
        if (
            !this.ext.isSupported(args.agentCard) ||
            (method !== "sendMessage" && method !== "sendMessageStream")
        ) {
            return;
        }

        // Timestamp outgoing message
        const sendMessageInput = args.input.value as SendMessageRequest;
        if (sendMessageInput.message) {
            this.ext.applyTimestamp(sendMessageInput.message);
        }

        // Request the extension via A2A-Extensions header
        if (!args.options) {
            args.options = {};
        }
        args.options.serviceParameters = ServiceParameters.createFrom(
            args.options.serviceParameters,
            withA2AExtensions(URI)
        );
    }

    async after(): Promise<void> {
        return;
    }
}
