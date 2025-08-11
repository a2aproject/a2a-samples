package com.samples.a2a;

import dev.langchain4j.service.UserMessage;
import jakarta.enterprise.context.ApplicationScoped;

import dev.langchain4j.service.SystemMessage;
import io.quarkiverse.langchain4j.RegisterAiService;

/**
 * Content editor agent interface for proofreading and polishing content.
 */
@RegisterAiService
@ApplicationScoped
public interface ContentEditorAgent {

    /**
     * Edits and polishes the provided content.
     *
     * @param assignment the content to be edited
     * @return the polished content
     */
    @SystemMessage("""
            You are an expert editor that can proof-read and polish content.

            Your output should only consist of the final polished content.
            """)
    String editContent(@UserMessage String assignment);
}
