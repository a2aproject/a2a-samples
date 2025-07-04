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
public class ContentEditorAgentCardProducer {

    @Inject
    @ConfigProperty(name = "quarkus.http.port")
    int httpPort;

    @Produces
    @PublicAgentCard
    public AgentCard agentCard() {
        return new AgentCard.Builder()
                .name("Content Editor Agent")
                .description("An agent that can proof-read and polish content.")
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
                        .id("editor")
                        .name("Edits content")
                        .description("Edits content by proof-reading and polishing")
                        .tags(List.of("writer"))
                        .examples(List.of("Edit the following article, make sure it has a professional tone"))
                        .build()))
                .protocolVersion("0.2.5")
                .build();
    }
}
