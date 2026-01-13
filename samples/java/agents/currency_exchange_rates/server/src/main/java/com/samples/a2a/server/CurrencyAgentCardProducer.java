package com.samples.a2a.server;

import io.a2a.server.PublicAgentCard;
import io.a2a.spec.AgentCapabilities;
import io.a2a.spec.AgentCard;
import io.a2a.spec.AgentSkill;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.enterprise.inject.Produces;
import java.util.List;
import org.eclipse.microprofile.config.inject.ConfigProperty;

@ApplicationScoped
public final class CurrencyAgentCardProducer {

  /** The HTTP port for the agent service. */
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
   * Produces the agent card for the currency agent.
   *
   * @return the configured agent card
   */
  @Produces
  @PublicAgentCard
  public AgentCard agentCard() {
    return new AgentCard.Builder()
        .name("Currency Agent")
        .description("Assistant for currency conversions")
        .url("http://localhost:" + getHttpPort())
        .version("1.0.0")
        .capabilities(
            new AgentCapabilities.Builder().streaming(true)
              .pushNotifications(true).build())
        .defaultInputModes(List.of("text"))
        .defaultOutputModes(List.of("text"))
        .skills(
        List.of(
        new AgentSkill.Builder()
          .id("convert_currency")
          .name("Currency Exchange Rates Tool")
          .description("Helps with exchange values between various currencies")
          .tags(List.of("currency conversion", "currency exchange"))
          .examples(List.of("What is exchange rate between USD and GBP?"))
          .build()))
        .build();
  }
}
