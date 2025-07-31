package com.samples.a2a;

import dev.langchain4j.service.SystemMessage;
import dev.langchain4j.service.UserMessage;
import io.quarkiverse.langchain4j.RegisterAiService;
import jakarta.enterprise.context.ApplicationScoped;

/**
 * Content Writer Agent interface for generating content based on outlines.
 */
@RegisterAiService
@ApplicationScoped
public interface ContentWriterAgent {

    /**
     * Writes content based on the provided assignment.
     *
     * @param assignment the content assignment with outline
     * @return the generated content
     */
    @SystemMessage("""
            You are an expert writer that can write a comprehensive and
            engaging piece of content based on a provided outline and a
            high-level description of the content.

            Do NOT attempt to write content without being given an outline.

            Your output should only consist of the final content.
            """)
    String writeContent(@UserMessage String assignment);
}
