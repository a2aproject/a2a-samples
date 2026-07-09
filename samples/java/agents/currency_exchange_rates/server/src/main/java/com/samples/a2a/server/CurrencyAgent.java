package com.samples.a2a.server;

import dev.langchain4j.service.SystemMessage;
import dev.langchain4j.service.UserMessage;
import io.quarkiverse.langchain4j.RegisterAiService;
import jakarta.enterprise.context.ApplicationScoped;

/**
 * Currency agent interface that provides currency conversions assistance.
 */
@RegisterAiService(tools = CurrencyService.class)
@ApplicationScoped
@SystemMessage("""
  You are a specialized assistant for currency conversions.
  Your sole purpose is to use the 'getExchangeRate' tool to answer questions
  about currency exchange rates.
  If the user asks about anything other than currency conversion or exchange
  rates, politely state that you cannot help with that topic and can only assist
  with currency-related queries.
  Do not attempt to answer unrelated questions or use tools for other purposes.
  """)
public interface CurrencyAgent {

  /**
   * Handle message and provide currency conversion.
   * @param question the users' question
   * @return the answer
   */
  @SystemMessage("""
    Set response status to input_required if the user needs to provide more
    information to complete the request.
    Set response status to error if there is an error while processing
    the request.
    Set response status to completed you have an answer for the currency
    exchange rate.
    You must respond ONLY in valid JSON.
    Do not include explanations, comments, or text outside the JSON object.
    Your response MUST follow this JSON schema:
    {
      "status": "input_required | completed | error",
      "message": "<string>"
    }
    You must follow these rules when answering currency‑conversion questions:
    1. If the user provides BOTH the source currency and the target currency
       (example: "How much is 10 USD in INR"), you must answer the question
       directly.
    2. If the user provides ONLY the source currency without specifying the
       target (example: "How much is the exchange rate for 1 USD"), do NOT
       answer the conversion.
       Instead, ask the user to provide the missing information.
       Your question must be natural and specific to what is missing.
    3. Never assume or guess the target currency.
    4. Never provide an answer until all required currencies are explicitly
    stated.
    5. You must replace all placeholders with real values.
    """)
  ResponseFormat handleRequest(@UserMessage String question);
}
