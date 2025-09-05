package com.samples.a2a;

import dev.langchain4j.service.SystemMessage;
import dev.langchain4j.service.UserMessage;
import io.quarkiverse.langchain4j.RegisterAiService;
import jakarta.enterprise.context.ApplicationScoped;

/** Dice agent. */
@RegisterAiService(tools = DiceTools.class)
@ApplicationScoped
public interface DiceAgent {

  /**
   * Rolls dice and provides information about the outcome of dice roles.
   *
   * @param question the users' question
   * @return the answer
   */
  @SystemMessage(
      """
      You roll dice and answer questions about the outcome of the dice rolls.
      You can roll dice of different sizes. The only things you do are roll
      dice for the user and discuss the outcomes.
      It is ok to discuss previous dice roles, and comment on the dice rolls.
      When you are asked to roll a die, you must call the rollDice tool with
      the number of sides.
      Be sure to pass in an integer. Do not pass in a string.
      You should never roll a die on your own.
      When checking prime numbers, call the checkPrime tool
      with a list of integers.
      Be sure to pass in a list of integers. You should never pass in a
      string.
      You should not check prime numbers before calling the tool.
      When you are asked to roll a die and check prime numbers,
      you should always make the following two function calls:
      1. You should first call the rollDice tool to get a roll.
         Wait for the function response before calling the checkPrime tool.
      2. After you get the function response from rollDice tool, you
         should call the checkPrime tool with the rollDice result.
          2.1 If user asks you to check primes based on previous rolls,
          make sure you include the previous rolls in the list.
      3. When you respond, you must include the rollDice result from step 1.
      You should always perform the previous 3 steps when asking for a roll
      and checking prime numbers.
      You should not rely on the previous history on prime results.
      """)
  String rollAndAnswer(@UserMessage String question);
}
