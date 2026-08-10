package com.samples.a2a;

import org.a2aproject.sdk.server.PublicAgentCard;
import org.a2aproject.sdk.spec.AgentCapabilities;
import org.a2aproject.sdk.spec.AgentCard;
import org.a2aproject.sdk.spec.AgentInterface;
import org.a2aproject.sdk.spec.AgentSkill;
import org.a2aproject.sdk.spec.ClientCredentialsOAuthFlow;
import org.a2aproject.sdk.spec.Legacy_0_3_AgentInterface;
import org.a2aproject.sdk.spec.OAuth2SecurityScheme;
import org.a2aproject.sdk.spec.OAuthFlows;
import org.a2aproject.sdk.spec.SecurityRequirement;
import org.a2aproject.sdk.spec.TransportProtocol;
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
    OAuth2SecurityScheme securityScheme = OAuth2SecurityScheme.builder()
            .flows(OAuthFlows.builder().clientCredentials(clientCredentialsOAuthFlow).build())
            .build();

    return AgentCard.builder()
        .name("Magic 8 Ball Agent")
        .description(
            "A mystical fortune-telling agent that answers your yes/no "
                + "questions by asking the all-knowing Magic 8 Ball oracle.")
        .preferredTransport(TransportProtocol.JSONRPC.asString())
        .url("http://localhost:" + httpPort)
        .version("1.0.0")
        .documentationUrl("http://example.com/docs")
        .capabilities(
            AgentCapabilities.builder()
                .streaming(true)
                .pushNotifications(false)
                .build())
        .defaultInputModes(List.of("text"))
        .defaultOutputModes(List.of("text"))
        .securityRequirements(List.of(
            SecurityRequirement.builder()
                .scheme(OAuth2SecurityScheme.TYPE, List.of("profile"))
                .build()))
        .securitySchemes(Map.of(OAuth2SecurityScheme.TYPE, securityScheme))
        .skills(
            List.of(
                AgentSkill.builder()
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
        .supportedInterfaces(
            List.of(
                new AgentInterface(
                    TransportProtocol.JSONRPC.asString(),
                        "http://localhost:" + httpPort),
                new AgentInterface(
                    TransportProtocol.HTTP_JSON.asString(),
                        "http://localhost:" + httpPort),
                new AgentInterface(TransportProtocol.GRPC.asString(),
                        "localhost:" + httpPort)))
        .additionalInterfaces(
            List.of(
                new Legacy_0_3_AgentInterface(
                    TransportProtocol.JSONRPC.asString(),
                        "http://localhost:" + httpPort),
                new Legacy_0_3_AgentInterface(
                    TransportProtocol.HTTP_JSON.asString(),
                        "http://localhost:" + httpPort),
                new Legacy_0_3_AgentInterface(TransportProtocol.GRPC.asString(),
                        "localhost:" + httpPort)))
        .build();
  }
}
