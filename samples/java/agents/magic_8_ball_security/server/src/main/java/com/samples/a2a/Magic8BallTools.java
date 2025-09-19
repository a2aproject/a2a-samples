package com.samples.a2a;

import dev.langchain4j.agent.tool.Tool;
import jakarta.enterprise.context.ApplicationScoped;
import java.util.concurrent.ThreadLocalRandom;

/** Service class that provides Magic 8 Ball fortune-telling functionality. */
@ApplicationScoped
public class Magic8BallTools {

  /** All possible Magic 8 Ball responses. */
  private static final String[] RESPONSES = {
    // Positive responses (10)
    "It is certain",
    "It is decidedly so",
    "Without a doubt",
    "Yes definitely",
    "You may rely on it",
    "As I see it, yes",
    "Most likely",
    "Outlook good",
    "Yes",
    "Signs point to yes",

    // Negative responses (5)
    "Don't count on it",
    "My reply is no",
    "My sources say no",
    "Outlook not so good",
    "Very doubtful",

    // Non-committal responses (5)
    "Better not tell you now",
    "Cannot predict now",
    "Concentrate and ask again",
    "Ask again later",
    "Reply hazy, try again"
  };

  /**
   * Get the response from the Magic 8 Ball.
   *
   * @param question the user's question
   * @return A random Magic 8 Ball response
   */
  @Tool("Get the response to the user's question from the Magic 8 Ball")
  public String shakeMagic8Ball(final String question) {
    int index = ThreadLocalRandom.current().nextInt(RESPONSES.length);
    String response = RESPONSES[index];
    System.out.println(
        "=== TOOL CALLED === Question: "
            + question
            + ", Index: "
            + index
            + ", Response: "
            + response);
    return response;
  }
}
