package com.samples.a2a;

import org.a2aproject.sdk.server.PublicAgentCard;
import org.a2aproject.sdk.spec.AgentCapabilities;
import org.a2aproject.sdk.spec.AgentCard;
import org.a2aproject.sdk.spec.AgentInterface;
import org.a2aproject.sdk.spec.AgentSkill;
import org.a2aproject.sdk.spec.TransportProtocol;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.enterprise.inject.Produces;
import jakarta.inject.Inject;
import java.util.Collections;
import java.util.List;
import org.eclipse.microprofile.config.inject.ConfigProperty;

/**
 * Producer for weather agent card configuration.
 * This class is final and not designed for extension.
 */
@ApplicationScoped
public final class WeatherAgentCardProducer {

  /** The HTTP port for the agent service. */
  @Inject
  @ConfigProperty(name = "quarkus.http.port")
  private int httpPort;

  /**
   * Gets the HTTP port.
   *
   * @return the HTTP port
   */
  public int getHttpPort() {
    return httpPort;
  }

  /**
   * Produces the agent card for the weather agent.
   *
   * @return the configured agent card
   */
  @Produces
  @PublicAgentCard
  public AgentCard agentCard() {
    return AgentCard.builder()
        .name("Weather Agent")
        .description("Helps with weather")
        .url("http://localhost:" + getHttpPort())
        .version("1.0.0")
        .capabilities(
            AgentCapabilities.builder()
                .streaming(true)
                .pushNotifications(false)
                .build())
        .defaultInputModes(Collections.singletonList("text"))
        .defaultOutputModes(Collections.singletonList("text"))
        .skills(
            Collections.singletonList(
                AgentSkill.builder()
                    .id("weather_search")
                    .name("Search weather")
                    .description("Helps with weather in city, or states")
                    .tags(Collections.singletonList("weather"))
                    .examples(List.of("weather in LA, CA"))
                    .build()))
        .supportedInterfaces(
            Collections.singletonList(
                new AgentInterface(
                    TransportProtocol.JSONRPC.asString(),
                    "http://localhost:" + getHttpPort())))
        .build();
  }
}
