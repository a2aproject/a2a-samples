import { AgentExtension, ExtensionURI } from '@a2a-js/sdk'

export const IN_TASK_OID4VP_EXTENSION_URI: ExtensionURI =
  'https://github.com/a2aproject/experimental-ext-oid4vp-auth/tree/main/v1'

export interface InTaskOpenId4VpAuthorizationRequest {
  client_id: string
  request_uri: string
}

export interface InTaskOpenId4VpMessageMetadata {
  authorizationRequest: InTaskOpenId4VpAuthorizationRequest
}

export interface InTaskOpenId4VpExtension extends AgentExtension {
  params: { oid4vpVersions: string[] }
}
