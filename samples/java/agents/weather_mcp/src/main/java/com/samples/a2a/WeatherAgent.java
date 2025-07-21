package com.samples.a2a;

import jakarta.enterprise.context.ApplicationScoped;
import jakarta.enterprise.context.SessionScoped;

import dev.langchain4j.service.SystemMessage;
import dev.langchain4j.service.UserMessage;
import io.quarkiverse.langchain4j.RegisterAiService;
import io.quarkiverse.langchain4j.mcp.runtime.McpToolBox;

@RegisterAiService
@ApplicationScoped
public interface WeatherAgent {

    @SystemMessage("""
            You are a specialized weather forecast assistant. Your primary function is to utilize the provided tools to
            retrieve and relay weather information in response to user queries. You must rely exclusively on these tools
            for data and refrain from inventing information. Ensure that all responses include the detailed output from
            the tools used and are formatted in Markdown.
            """
    )
    @McpToolBox("weather")
    String chat(@UserMessage String question);
}
