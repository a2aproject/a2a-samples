package com.samples.a2a;

import dev.langchain4j.service.MemoryId;
import dev.langchain4j.service.SystemMessage;
import dev.langchain4j.service.UserMessage;
import io.quarkiverse.langchain4j.RegisterAiService;
import jakarta.enterprise.context.ApplicationScoped;

/** Magic 8 Ball fortune-telling agent. */
@RegisterAiService(tools = Magic8BallTools.class)
@ApplicationScoped
public interface Magic8BallAgent {

  /**
   * Answers questions using the mystical powers of the Magic 8 Ball.
   *
   * @param memoryId unique identifier for this conversation
   * @param question the users' question
   * @return the Magic 8 Ball's response
   */
  @SystemMessage(
      """
      You shake a Magic 8 Ball to answer questions.
      The only thing you do is shake the Magic 8 Ball to answer
      the user's question and then discuss the response.
      When you are asked to answer a question, you must call the
      shakeMagic8Ball tool with the user's question.
      You should never rely on the previous history for Magic 8 Ball
      responses. Call the shakeMagic8Ball tool for each question.
      You should never shake the Magic 8 Ball on your own.
      You must always call the tool.
      When you are asked a question, you should always make the following
      function call:
      1. You should first call the shakeMagic8Ball tool to get the response.
      Wait for the function response.
      2. After you get the function response, relay the response to the user.
      You should not rely on the previous history for Magic 8 Ball responses.
      """)
  String answerQuestion(@MemoryId String memoryId,
                        @UserMessage String question);
}
