package com.samples.a2a;

import java.util.Collections;
import java.util.List;

import jakarta.enterprise.context.ApplicationScoped;
import jakarta.enterprise.inject.Produces;
import jakarta.inject.Inject;

import io.a2a.server.PublicAgentCard;
import io.a2a.spec.AgentCapabilities;
import io.a2a.spec.AgentCard;
import io.a2a.spec.AgentSkill;

import org.eclipse.microprofile.config.inject.ConfigProperty;

@ApplicationScoped
public class ContentWriterAgentCardProducer {

    @Inject
    @ConfigProperty(name = "quarkus.http.port")
    int httpPort;

    @Produces
    @PublicAgentCard
    public AgentCard agentCard() {
        return new AgentCard.Builder()
                .name("Content Writer Agent")
                .description("An agent that can write a comprehensive and engaging piece of content based on the" +
                        " provided outline and high-level description of the content")
                .url("http://localhost:" + httpPort)
                .version("1.0.0")
                .documentationUrl("http://example.com/docs")
                .capabilities(new AgentCapabilities.Builder()
                        .streaming(true)
                        .pushNotifications(false)
                        .stateTransitionHistory(false)
                        .build())
                .defaultInputModes(Collections.singletonList("text"))
                .defaultOutputModes(Collections.singletonList("text"))
                .skills(Collections.singletonList(new AgentSkill.Builder()
                        .id("writer")
                        .name("Writes content using an outline")
                        .description("Writes content using a given outline and high-level description of the content")
                        .tags(List.of("writer"))
                        .examples(List.of("Write a short, upbeat, and encouraging twitter post about learning Java. Base your writing on the given outline."))
                        .build()))
                .protocolVersion("0.2.5")
                .build();
    }
}
