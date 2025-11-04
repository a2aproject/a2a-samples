package com.samples.a2a.client;

import com.samples.a2a.client.util.EventHandlerUtil;
import io.a2a.client.Client;
import io.a2a.client.ClientEvent;
import io.a2a.client.config.ClientConfig;
import io.a2a.client.transport.grpc.GrpcTransport;
import io.a2a.client.transport.grpc.GrpcTransportConfigBuilder;
import io.a2a.client.transport.jsonrpc.JSONRPCTransport;
import io.a2a.client.transport.jsonrpc.JSONRPCTransportConfigBuilder;
import io.a2a.client.transport.rest.RestTransport;
import io.a2a.client.transport.rest.RestTransportConfigBuilder;
import io.a2a.client.transport.spi.interceptors.auth.AuthInterceptor;
import io.a2a.client.transport.spi.interceptors.auth.CredentialService;
import io.a2a.spec.AgentCard;
import io.grpc.Channel;
import io.grpc.ManagedChannelBuilder;
import java.util.List;
import java.util.concurrent.CompletableFuture;
import java.util.function.BiConsumer;
import java.util.function.Consumer;
import java.util.function.Function;

/**
 * Test client utility for creating A2A clients with HTTP-based transports
 * and OAuth2 authentication.
 *
 * <p>This class encapsulates the complexity of setting up A2A clients with
 * multiple transport options (gRPC, REST, JSON-RPC) and Keycloak OAuth2
 * authentication, providing simple methods to create configured clients
 * for testing and development.
 */
public final class TestClient {

  private TestClient() {
  }

  /**
   * Creates an A2A client with the specified transport and
   * OAuth2 authentication.
   *
   * @param agentCard the agent card to connect to
   * @param messageResponse CompletableFuture for handling responses
   * @param transport the transport type to use ("grpc", "rest", or "jsonrpc")
   * @return configured A2A client
   */
  public static Client createClient(
      final AgentCard agentCard,
      final CompletableFuture<String> messageResponse,
      final String transport) {

    // Create consumers for handling client events
    List<BiConsumer<ClientEvent, AgentCard>> consumers =
        EventHandlerUtil.createEventConsumers(messageResponse);

    // Create error handler for streaming errors
    Consumer<Throwable> streamingErrorHandler =
        EventHandlerUtil.createStreamingErrorHandler(messageResponse);

    // Create credential service for OAuth2 authentication
    CredentialService credentialService
            = new KeycloakOAuth2CredentialService();

    // Create shared auth interceptor for all transports
    AuthInterceptor authInterceptor = new AuthInterceptor(credentialService);

    // Create channel factory for gRPC transport
    Function<String, Channel> channelFactory =
        agentUrl -> {
          return ManagedChannelBuilder
                  .forTarget(agentUrl)
                  .usePlaintext()
                  .build();
        };

    // Create the A2A client with the specified transport
    try {
      var builder =
          Client.builder(agentCard)
              .addConsumers(consumers)
              .streamingErrorHandler(streamingErrorHandler);

      // Configure only the specified transport
      switch (transport.toLowerCase()) {
        case "grpc":
          builder.withTransport(
              GrpcTransport.class,
              new GrpcTransportConfigBuilder()
                  .channelFactory(channelFactory)
                  .addInterceptor(authInterceptor) // auth config
                  .build());
          break;
        case "rest":
          builder.withTransport(
              RestTransport.class,
              new RestTransportConfigBuilder()
                  .addInterceptor(authInterceptor) // auth config
                  .build());
          break;
        case "jsonrpc":
          builder.withTransport(
              JSONRPCTransport.class,
              new JSONRPCTransportConfigBuilder()
                  .addInterceptor(authInterceptor) // auth config
                  .build());
          break;
        default:
          throw new IllegalArgumentException(
              "Unsupported transport type: "
                  + transport
                  + ". Supported types are: grpc, rest, jsonrpc");
      }

      return builder.clientConfig(new ClientConfig.Builder().build()).build();
    } catch (Exception e) {
      throw new RuntimeException("Failed to create A2A client", e);
    }
  }
}
