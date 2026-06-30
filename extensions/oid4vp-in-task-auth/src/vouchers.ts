import { SdJwtVcRecord } from '@credo-ts/core'
import { createDidKidVerificationMethod, CredoAgentWithOpenId4Vc } from './credo-helpers'
import { PARTNERS, PartnerKey } from './partners'

const HOLDER_SECRET_KEY = '86213c3d7fc8d4d6754c7a0fd969598e'

export const DISCOUNT_VOUCHER_VCT = 'DiscountVoucher'

/** Per-voucher claims set at issuance time (`vct` and `issuer_brand` are derived from the partner). */
export interface VoucherClaims {
  percent_off: number
  expires_at: string
  voucher_id: string
}

/** Full SD-JWT payload. The index signature lets it satisfy Credo's `SdJwtVcPayload`. */
export interface DiscountVoucherClaims extends VoucherClaims {
  vct: typeof DISCOUNT_VOUCHER_VCT
  issuer_brand: string
  [claim: string]: unknown
}

interface VoucherDefinition {
  partner: PartnerKey
  issuerSeed: string
  claims: VoucherClaims
}

const FAR_FUTURE_EXPIRY = '2027-01-01T00:00:00Z'

const VOUCHER_DEFINITIONS: VoucherDefinition[] = [
  {
    partner: 'AURORA',
    issuerSeed: 'a1213c3d7fc8d4d6754c7a0fd969598e',
    claims: { percent_off: 25, expires_at: FAR_FUTURE_EXPIRY, voucher_id: 'aurora-gold-0001' },
  },
  {
    partner: 'MERIDIAN',
    issuerSeed: 'b2213c3d7fc8d4d6754c7a0fd969598e',
    claims: { percent_off: 10, expires_at: FAR_FUTURE_EXPIRY, voucher_id: 'meridian-silver-0002' },
  },
  {
    partner: 'BARGAIN',
    issuerSeed: 'c3213c3d7fc8d4d6754c7a0fd969598e',
    claims: { percent_off: 50, expires_at: FAR_FUTURE_EXPIRY, voucher_id: 'bargain-bronze-0003' },
  },
]

const DISCLOSURE_FRAME = {
  _sd: ['issuer_brand', 'percent_off', 'expires_at', 'voucher_id'],
}

export interface ProvisionedVoucher {
  brand: string
  percentOff: number
  expiresAt: string
}

/**
 * Issues every {@link VOUCHER_DEFINITIONS} entry into the holder wallet and returns a summary
 * for display. Asserts each derived issuer DID matches the hardcoded one in `partners.ts`.
 */
export async function provisionVouchers(credoAgent: CredoAgentWithOpenId4Vc): Promise<ProvisionedVoucher[]> {
  const { kid: holderKid } = await createDidKidVerificationMethod(credoAgent.context, HOLDER_SECRET_KEY)

  const provisioned: ProvisionedVoucher[] = []

  for (const definition of VOUCHER_DEFINITIONS) {
    const partner = PARTNERS[definition.partner]
    const { kid: issuerKid, did: issuerDid } = await createDidKidVerificationMethod(
      credoAgent.context,
      definition.issuerSeed
    )

    if (issuerDid !== partner.issuerDid) {
      throw new Error(
        `Issuer DID mismatch for partner ${partner.id}: derived "${issuerDid}" from the seed, ` +
          `but partners.ts declares "${partner.issuerDid}". Re-derive and update partners.ts.`
      )
    }

    const claims: DiscountVoucherClaims = {
      vct: DISCOUNT_VOUCHER_VCT,
      issuer_brand: partner.name,
      ...definition.claims,
    }

    const signed = await credoAgent.sdJwtVc.sign({
      holder: { method: 'did', didUrl: holderKid },
      issuer: { method: 'did', didUrl: issuerKid },
      payload: claims,
      disclosureFrame: DISCLOSURE_FRAME,
    })

    await credoAgent.sdJwtVc.store({
      record: new SdJwtVcRecord({
        credentialInstances: [{ compactSdJwtVc: signed.compact }],
      }),
    })

    provisioned.push({
      brand: partner.name,
      percentOff: claims.percent_off,
      expiresAt: claims.expires_at,
    })
  }

  return provisioned
}
