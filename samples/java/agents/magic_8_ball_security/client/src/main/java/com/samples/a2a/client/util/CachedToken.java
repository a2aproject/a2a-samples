package com.samples.a2a.client.util;

/**
 * Represents a cached token with expiration information.
 *
 * <p>This utility class is used to cache OAuth2 access tokens and
 * provides expiration checking to avoid using expired tokens.
 */
public final class CachedToken {
  /** Expiration buffer. */
  private static final long EXPIRATION_BUFFER_MS = 5 * 60 * 1000; // 5 minutes

  /** Converstion to milliseconds. */
  private static final long SECONDS_TO_MS = 1000;

  /** Cached token. */
  private final String token;

  /** Expiration time. */
  private final long expirationTime;

  /**
   * Creates a new CachedToken with the specified token and expiration time.
   *
   * @param token the access token string
   * @param expirationTime the expiration time in milliseconds since epoch
   */
  public CachedToken(final String token, final long expirationTime) {
    this.token = token;
    this.expirationTime = expirationTime;
  }

  /**
   * Gets the cached token.
   *
   * @return the access token string
   */
  public String getToken() {
    return token;
  }

  /**
   * Gets the expiration time.
   *
   * @return the expiration time in milliseconds since epoch
   */
  public long getExpirationTime() {
    return expirationTime;
  }

  /**
   * Checks if the token is expired or will expire soon.
   *
   * <p>Returns true if the token will expire within 5 minutes to provide
   * a buffer for token refresh.
   *
   * @return true if the token is expired or will expire soon
   */
  public boolean isExpired() {
    // Consider token expired if it expires within 5 minutes (300,000 ms)
    return System.currentTimeMillis()
            >= (expirationTime - EXPIRATION_BUFFER_MS);
  }

  /**
   * Creates a CachedToken from an access token response
   * with expires_in seconds.
   *
   * @param token the access token string
   * @param expiresInSeconds the number of seconds until expiration
   * @return a new CachedToken instance
   */
  public static CachedToken fromExpiresIn(final String token,
                                          final long expiresInSeconds) {
    long expirationTime = System.currentTimeMillis()
            + (expiresInSeconds * SECONDS_TO_MS);
    return new CachedToken(token, expirationTime);
  }

  @Override
  public String toString() {
    return "CachedToken{"
        + "token=***"
        + // Don't log the actual token for security
        ", expirationTime="
        + expirationTime
        + ", expired="
        + isExpired()
        + '}';
  }
}
