package com.samples.a2a.server;

import com.fasterxml.jackson.databind.ObjectMapper;
import dev.langchain4j.agent.tool.Tool;
import jakarta.enterprise.context.ApplicationScoped;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.util.Map;

@ApplicationScoped
public final class CurrencyService {

  /**
   * Object mapper to use.
   */
  private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper();
  /**
   * ERROR_CODE_400 to use.
   */
  public static final int ERROR_CODE_400 = 400;
  /**
   * HttpClient to use.
   */
  private final HttpClient client = HttpClient.newBuilder().build();

  /**
   * Provides currency conversions from one to another currency.
   *
   * @param currencyFrom source currency
   * @param currencyTo   target currency
   * @return currency‑conversion rate
   */
  @Tool("Provides currency conversions from one to another currency")
  public Map<String, Object> getExchangeRate(final String currencyFrom,
                                             final String currencyTo) {
    String url = "https://api.frankfurter.app/latest";
    URI uri = URI.create(url + "?from=%s&to=%s".formatted(currencyFrom,
      currencyTo));
    try {
      HttpRequest request = HttpRequest.newBuilder()
        .uri(uri)
        .GET()
        .build();
      HttpResponse<String> response = client.send(request,
        HttpResponse.BodyHandlers.ofString());

      if (response.statusCode() >= ERROR_CODE_400) {
        throw new RuntimeException("Request exchange rate failed with status "
          + response.statusCode());
      }

      Map<String, Object> data = OBJECT_MAPPER.readValue(response.body(),
        Map.class);
      if (data == null || !data.containsKey("rates")) {
        throw new RuntimeException(
          "Invalid API response format from Frankfurter API");
      }
      return data;
    } catch (IOException | InterruptedException e) {
      throw new RuntimeException("Request exchange rate failed.", e);
    }
  }
}
