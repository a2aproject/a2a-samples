package com.samples.a2a;

import dev.langchain4j.service.UserMessage;
import jakarta.enterprise.context.ApplicationScoped;

import dev.langchain4j.service.SystemMessage;
import io.quarkiverse.langchain4j.RegisterAiService;

@RegisterAiService
@ApplicationScoped
public interface ContentWriterAgent {

    @SystemMessage("""
            You are an expert writer that can write a comprehensive and engaging piece of content based on a 
            provided outline and a high-level description of the content.
            
            Do NOT attempt to write content without being given an outline.
            
            Your output should only consist of the final content. 
            """
    )
    String writeContent(@UserMessage String assignment);
}
