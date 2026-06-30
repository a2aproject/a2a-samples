import { ClaimFormat, DcqlQuery } from '@credo-ts/core'
import { findBrandNameForIssuer, isTrustedIssuer } from '../partners'
import { DISCOUNT_VOUCHER_VCT } from '../vouchers'

export const VOUCHER_DCQL_QUERY_ID = 'voucher'

export const VOUCHER_DCQL_QUERY = {
  credentials: [
    {
      id: VOUCHER_DCQL_QUERY_ID,
      format: ClaimFormat.SdJwtW3cVc,
      meta: { vct_values: [DISCOUNT_VOUCHER_VCT] },
      claims: [{ path: ['percent_off'] }, { path: ['expires_at'] }],
    },
  ],
  credential_sets: [{ options: [[VOUCHER_DCQL_QUERY_ID]], purpose: 'Apply partner discount' }],
} satisfies DcqlQuery

export interface AppliedDiscount {
  percentOff: number
  brand?: string
}

export interface AuthResult {
  approved: boolean
  discount?: AppliedDiscount
  reason?: string
}

export function evaluateVoucherClaims(claims: Record<string, unknown>): AuthResult {
  const issuerDid = String(claims.iss ?? '')
  const percentOff = Number(claims.percent_off)
  const expiresAt = String(claims.expires_at ?? '')

  const now = Date.now()

  if (!isTrustedIssuer(issuerDid)) {
    return { approved: false, reason: `issuer ${issuerDid} is not one of our partner brands` }
  }
  if (expiresAt) {
    const expiryTime = new Date(expiresAt).getTime()
    if (!Number.isFinite(expiryTime)) {
      return { approved: false, reason: `the voucher had an unreadable expiry (${expiresAt})` }
    }
    if (expiryTime < now) {
      return { approved: false, reason: `the voucher expired on ${expiresAt}` }
    }
  }
  if (!Number.isFinite(percentOff) || percentOff <= 0 || percentOff > 100) {
    return { approved: false, reason: 'the voucher did not disclose a valid discount' }
  }

  return { approved: true, discount: { percentOff, brand: findBrandNameForIssuer(issuerDid) } }
}
