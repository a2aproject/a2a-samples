package com.samples.a2a;

import dev.langchain4j.service.UserMessage;
import jakarta.enterprise.context.ApplicationScoped;

import dev.langchain4j.service.SystemMessage;
import io.quarkiverse.langchain4j.RegisterAiService;

@RegisterAiService
@ApplicationScoped
public interface ContentEditorAgent {

    @SystemMessage("""
            You are an expert editor that can proof-read and polish content.
            
            Your output should only consist of the final polished content.
            """
    )
    String editContent(@UserMessage String assignment);
}
