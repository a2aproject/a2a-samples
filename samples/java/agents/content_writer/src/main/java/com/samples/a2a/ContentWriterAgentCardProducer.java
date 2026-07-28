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

/** Producer for Content Writer Agent Card. */
@ApplicationScoped
public final class ContentWriterAgentCardProducer {

  /** HTTP port for the agent. */
  @Inject
  @ConfigProperty(name = "quarkus.http.port")
  private int httpPort;

  /**
   * Creates the agent card for the content writer agent.
   *
   * @return the agent card
   */
  @Produces
  @PublicAgentCard
  public AgentCard agentCard() {
    return AgentCard.builder()
        .name("Content Writer Agent")
        .description(
            "An agent that can write a "
                + "comprehensive and engaging piece of content "
                + "based on the provided outline and high-level "
                + "description of the content")
        .url("http://localhost:" + httpPort)
        .version("1.0.0")
        .documentationUrl("http://example.com/docs")
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
                    .id("writer")
                    .name("Writes content using an outline")
                    .description(
                        "Writes content using a given "
                            + "outline and high-level description of "
                            + "the content")
                    .tags(List.of("writer"))
                    .examples(
                        List.of(
                            "Write a short, upbeat, and "
                                + "encouraging twitter post about learning "
                                + "Java. Base your writing on the given "
                                + "outline."))
                    .build()))
        .supportedInterfaces(
            Collections.singletonList(
                new AgentInterface(
                    TransportProtocol.JSONRPC.asString(),
                    "http://localhost:" + httpPort)))
        .build();
  }
}
