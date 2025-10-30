package com.samples.a2a.client.util;

import java.io.InputStream;
import java.util.concurrent.ConcurrentMap;
import org.keycloak.authorization.client.AuthzClient;
import org.keycloak.representations.AccessTokenResponse;

/** Utility class for common Keycloak operations and token caching. */
public final class KeycloakUtil {

  private KeycloakUtil() {
    // Utility class, prevent instantiation
  }

  /**
   * Creates a Keycloak AuthzClient from the default keycloak.json
   * configuration file.
   *
   * @return a configured AuthzClient
   * @throws IllegalArgumentException if keycloak.json cannot be found/loaded
   */
  public static AuthzClient createAuthzClient() {
    return createAuthzClient("keycloak.json");
  }

  private static AuthzClient createAuthzClient(final String configFileName) {
    try {
      InputStream configStream = null;

      // First try to load from current directory (for JBang)
      try {
        java.io.File configFile = new java.io.File(configFileName);
        if (configFile.exists()) {
          configStream = new java.io.FileInputStream(configFile);
        }
      } catch (Exception ignored) {
        // Fall back to classpath
      }

      // If not found in current directory, try classpath
      if (configStream == null) {
        configStream = KeycloakUtil.class
                .getClassLoader()
                .getResourceAsStream(configFileName);
      }

      if (configStream == null) {
        throw new IllegalArgumentException("Config file not found: "
                + configFileName);
      }

      return AuthzClient.create(configStream);
    } catch (Exception e) {
      throw new IllegalArgumentException(
          "Failed to load Keycloak configuration from " + configFileName, e);
    }
  }

  /**
   * Gets a valid access token for the specified cache key, using the
   * provided cache and AuthzClient. Uses caching to avoid unnecessary
   * token requests.
   *
   * @param cacheKey the cache key to use for storing/retrieving the token
   * @param tokenCache the concurrent map to use for token caching
   * @param authzClient the Keycloak AuthzClient to use for token requests
   * @return a valid access token
   * @throws RuntimeException if token acquisition fails
   */
  public static String getAccessToken(
      final String cacheKey,
      final ConcurrentMap<String,CachedToken> tokenCache, final AuthzClient authzClient) {
    CachedToken cached = tokenCache.get(cacheKey);

    // Check if we have a valid cached token
    if (cached != null && !cached.isExpired()) {
      return cached.getToken();
    }

    try {
      // Obtain a new access token from Keycloak
      AccessTokenResponse tokenResponse = authzClient.obtainAccessToken();

      // Cache the token with expiration info
      CachedToken newToken =
          CachedToken.fromExpiresIn(tokenResponse.getToken(),
                  tokenResponse.getExpiresIn());
      tokenCache.put(cacheKey, newToken);

      return tokenResponse.getToken();
    } catch (Exception e) {
      throw new RuntimeException("Failed to obtain token from Keycloak", e);
    }
  }
}
