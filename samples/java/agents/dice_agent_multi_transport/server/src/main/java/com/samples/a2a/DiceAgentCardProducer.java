package com.samples.a2a;

import io.a2a.server.PublicAgentCard;
import io.a2a.spec.AgentCapabilities;
import io.a2a.spec.AgentCard;
import io.a2a.spec.AgentInterface;
import io.a2a.spec.AgentSkill;
import io.a2a.spec.TransportProtocol;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.enterprise.inject.Produces;
import jakarta.inject.Inject;
import java.util.List;
import org.eclipse.microprofile.config.inject.ConfigProperty;

/**
 * Producer for dice agent card configuration.
 */
@ApplicationScoped
public final class DiceAgentCardProducer {

  /** The HTTP port for the agent service. */
  @Inject
  @ConfigProperty(name = "quarkus.http.port")
  private int httpPort;

  /**
   * Produces the agent card for the dice agent.
   *
   * @return the configured agent card
   */
  @Produces
  @PublicAgentCard
  public AgentCard agentCard() {
    return new AgentCard.Builder()
        .name("Dice Agent")
        .description(
            "Rolls an N-sided dice and answers questions about the "
                + "outcome of the dice rolls. Can also answer questions "
                + "about prime numbers.")
        .preferredTransport(TransportProtocol.GRPC.asString())
        .url("localhost:" + httpPort)
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
        .skills(
            List.of(
                new AgentSkill.Builder()
                    .id("dice_roller")
                    .name("Roll dice")
                    .description("Rolls dice and discusses outcomes")
                    .tags(List.of("dice", "games", "random"))
                    .examples(
                        List.of("Can you roll a 6-sided die?"))
                    .build(),
                new AgentSkill.Builder()
                    .id("prime_checker")
                    .name("Check prime numbers")
                    .description("Checks if given numbers are prime")
                    .tags(List.of("math", "prime", "numbers"))
                    .examples(
                        List.of(
                            "Is 17 a prime number?",
                            "Which of these numbers are prime: 1, 4, 6, 7"))
                    .build()))
        .protocolVersion("0.3.0")
        .additionalInterfaces(
            List.of(
                new AgentInterface(TransportProtocol.GRPC.asString(),
                        "localhost:" + httpPort),
                new AgentInterface(
                    TransportProtocol.JSONRPC.asString(),
                        "http://localhost:" + httpPort)))
        .build();
  }
}
