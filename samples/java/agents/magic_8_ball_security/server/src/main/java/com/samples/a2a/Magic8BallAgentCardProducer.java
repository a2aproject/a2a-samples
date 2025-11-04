package com.samples.a2a;

import io.a2a.server.PublicAgentCard;
import io.a2a.spec.AgentCapabilities;
import io.a2a.spec.AgentCard;
import io.a2a.spec.AgentInterface;
import io.a2a.spec.AgentSkill;
import io.a2a.spec.ClientCredentialsOAuthFlow;
import io.a2a.spec.OAuth2SecurityScheme;
import io.a2a.spec.OAuthFlows;
import io.a2a.spec.TransportProtocol;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.enterprise.inject.Produces;
import jakarta.inject.Inject;
import java.util.List;
import java.util.Map;
import org.eclipse.microprofile.config.inject.ConfigProperty;

/** Producer for Magic 8 Ball agent card configuration. */
@ApplicationScoped
public final class Magic8BallAgentCardProducer {

  /** The HTTP port for the agent service. */
  @Inject
  @ConfigProperty(name = "quarkus.http.port")
  private int httpPort;

  /** The HTTP port for Keycloak. */
  @Inject
  @ConfigProperty(name = "quarkus.keycloak.devservices.port")
  private int keycloakPort;

  /**
   * Produces the agent card for the Magic 8 Ball agent.
   *
   * @return the configured agent card
   */
  @Produces
  @PublicAgentCard
  public AgentCard agentCard() {
    ClientCredentialsOAuthFlow clientCredentialsOAuthFlow = new ClientCredentialsOAuthFlow(
            null,
            Map.of("openid", "openid", "profile", "profile"),
            "http://localhost:" + keycloakPort + "/realms/quarkus/protocol/openid-connect/token");
    OAuth2SecurityScheme securityScheme = new OAuth2SecurityScheme.Builder()
            .flows(new OAuthFlows.Builder().clientCredentials(clientCredentialsOAuthFlow).build())
            .build();

    return new AgentCard.Builder()
        .name("Magic 8 Ball Agent")
        .description(
            "A mystical fortune-telling agent that answers your yes/no "
                + "questions by asking the all-knowing Magic 8 Ball oracle.")
        .preferredTransport(TransportProtocol.JSONRPC.asString())
        .url("http://localhost:" + httpPort)
        .version("1.0.0")
        .documentationUrl("http://example.com/docs")
        .capabilities(
            new AgentCapabilities.Builder()
                .streaming(true)
                .pushNotifications(false)
                .stateTransitionHistory(false)
                .build())
        .defaultInputModes(List.of("text"))
        .defaultOutputModes(List.of("text"))
        .security(List.of(Map.of(OAuth2SecurityScheme.OAUTH2,
                List.of("profile"))))
        .securitySchemes(Map.of(OAuth2SecurityScheme.OAUTH2, securityScheme))
        .skills(
            List.of(
                new AgentSkill.Builder()
                    .id("magic_8_ball")
                    .name("Magic 8 Ball Fortune Teller")
                    .description("Uses a Magic 8 Ball to answer"
                            + " yes/no questions")
                    .tags(List.of("fortune", "magic-8-ball", "oracle"))
                    .examples(
                        List.of(
                            "Should I deploy this code on Friday?",
                            "Will my tests pass?",
                            "Is this a good idea?"))
                    .build()))
        .protocolVersion("0.3.0")
        .additionalInterfaces(
            List.of(
                new AgentInterface(
                    TransportProtocol.JSONRPC.asString(),
                        "http://localhost:" + httpPort),
                new AgentInterface(
                    TransportProtocol.HTTP_JSON.asString(),
                        "http://localhost:" + httpPort),
                new AgentInterface(TransportProtocol.GRPC.asString(),
                        "localhost:" + httpPort)))
        .build();
  }
}
