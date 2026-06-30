import { DcqlCredentialsForRequest, DcqlQueryResult, DcqlValidCredential, SdJwtVcRecord } from '@credo-ts/core'
import { CredoAgentWithOpenId4Vc } from './credo-helpers'

/** One per-credential entry of a {@link DcqlCredentialsForRequest}. */
type DcqlCredentialEntry = DcqlCredentialsForRequest[string][number]

export interface VoucherOption {
  claims: Record<string, unknown>
  requestedClaims: Record<string, unknown>
  match: DcqlValidCredential
}

export interface PresentationChoice {
  choose: (options: VoucherOption[], purpose: string | undefined) => Promise<VoucherOption | null>
  confirm: (requestedClaims: Record<string, unknown>) => Promise<boolean>
}

export type PresentationOutcome =
  | { status: 'sent' }
  | { status: 'declined' }
  | { status: 'unsatisfiable' }
  | { status: 'failed'; detail: string }

function disclosedClaims(match: DcqlValidCredential): Record<string, unknown> {
  return Object.assign({}, ...(match.claims.valid_claims ?? []).map((claim) => claim.output))
}

function readVoucherClaims(
  credoAgent: CredoAgentWithOpenId4Vc,
  record: DcqlValidCredential['record']
): Record<string, unknown> {
  // The demo only issues SD-JWT VCs; narrow to that record type to read its compact encoding.
  if (!(record instanceof SdJwtVcRecord)) {
    throw new Error(`Expected an SD-JWT VC record, got ${record.constructor?.name ?? 'unknown'}`)
  }
  const compact = record.credentialInstances[0]?.compactSdJwtVc ?? ''
  return credoAgent.sdJwtVc.fromCompact(compact).prettyClaims as Record<string, unknown>
}

/**
 * Builds the {@link DcqlCredentialEntry} for the CHOSEN credential. `selectCredentialsForDcqlRequest`
 * auto-picks the first match, so we reuse its result only as a template for the correct `claimFormat`
 * (it routes presentation to the right SD-JWT service) and swap in the chosen record plus the claims
 * Credo already computed for selective disclosure.
 */
export function buildChosenEntry(template: DcqlCredentialEntry, chosen: VoucherOption): DcqlCredentialEntry {
  // Credo's static type maps `vc+sd-jwt` to a W3cV2 record, but at runtime our voucher is stored as
  // an SdJwtVcRecord. The cast bridges that single divergence, everything else is fully typed.
  return {
    ...template,
    credentialRecord: chosen.match.record,
    disclosedPayload: chosen.requestedClaims,
  } as DcqlCredentialEntry
}

export async function presentVoucher(
  credoAgent: CredoAgentWithOpenId4Vc,
  requestUri: string,
  choice: PresentationChoice
): Promise<PresentationOutcome> {
  const resolved = await credoAgent.openid4vc.holder.resolveOpenId4VpAuthorizationRequest(requestUri)
  const queryResult: DcqlQueryResult | undefined = resolved.dcql?.queryResult

  if (!queryResult?.can_be_satisfied) {
    return { status: 'unsatisfiable' }
  }

  const template = credoAgent.openid4vc.holder.selectCredentialsForDcqlRequest(queryResult)
  const queryId = Object.keys(template)[0]
  const match = queryResult.credential_matches[queryId]
  if (!match.success) return { status: 'unsatisfiable' }

  const rawPurpose = queryResult.credential_sets?.[0]?.purpose
  const purpose = typeof rawPurpose === 'string' ? rawPurpose : undefined

  // Credo attaches the stored `record` to every match, but TS doesn't surface it through the
  // discriminated-union narrowing above — assert it back.
  const validCredentials = match.valid_credentials as DcqlValidCredential[]

  const options: VoucherOption[] = validCredentials.map((credential) => ({
    match: credential,
    claims: readVoucherClaims(credoAgent, credential.record),
    requestedClaims: disclosedClaims(credential),
  }))

  const chosen = await choice.choose(options, purpose)
  if (!chosen) return { status: 'declined' }

  if (!(await choice.confirm(chosen.requestedClaims))) return { status: 'declined' }

  const entry = buildChosenEntry(template[queryId][0], chosen)
  const result = await credoAgent.openid4vc.holder.acceptOpenId4VpAuthorizationRequest({
    authorizationRequestPayload: resolved.authorizationRequestPayload,
    dcql: { credentials: { [queryId]: [entry] } },
  })

  return result.ok ? { status: 'sent' } : { status: 'failed', detail: JSON.stringify(result).slice(0, 200) }
}
