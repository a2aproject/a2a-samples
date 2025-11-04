package com.samples.a2a.client;

import com.samples.a2a.client.util.CachedToken;
import com.samples.a2a.client.util.KeycloakUtil;
import io.a2a.client.transport.spi.interceptors.ClientCallContext;
import io.a2a.client.transport.spi.interceptors.auth.CredentialService;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentMap;
import org.keycloak.authorization.client.AuthzClient;

/**
 * A CredentialService implementation that provides OAuth2 access tokens
 * using Keycloak. This service is used by the A2A client transport
 * authentication interceptors.
 */
public final class KeycloakOAuth2CredentialService implements CredentialService {

  /** OAuth2 scheme name. */
  private static final String OAUTH2_SCHEME_NAME = "oauth2";

  /** Token cache. */
  private final ConcurrentMap<String, CachedToken> tokenCache
          = new ConcurrentHashMap<>();

  /** Keycloak authz client. */
  private final AuthzClient authzClient;

  /**
   * Creates a new KeycloakOAuth2CredentialService using the
   * default keycloak.json file.
   *
   * @throws IllegalArgumentException if keycloak.json cannot be found/loaded
   */
  public KeycloakOAuth2CredentialService() {
    this.authzClient = KeycloakUtil.createAuthzClient();
  }

  @Override
  public String getCredential(final String securitySchemeName,
                              final ClientCallContext clientCallContext) {
    if (!OAUTH2_SCHEME_NAME.equals(securitySchemeName)) {
      throw new IllegalArgumentException("Unsupported security scheme: "
              + securitySchemeName);
    }

    try {
      return KeycloakUtil.getAccessToken(securitySchemeName,
              tokenCache, authzClient);
    } catch (Exception e) {
      throw new RuntimeException(
          "Failed to obtain OAuth2 access token for scheme: "
                  + securitySchemeName, e);
    }
  }
}
