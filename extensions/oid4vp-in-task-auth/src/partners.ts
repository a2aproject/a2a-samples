export interface PartnerBrand {
  id: string
  name: string
  issuerDid: string
}

export type PartnerKey = 'AURORA' | 'MERIDIAN' | 'BARGAIN'

export const PARTNERS: Record<PartnerKey, PartnerBrand> = {
  AURORA: {
    id: 'AURORA',
    name: 'Aurora Airlines Rewards',
    issuerDid: 'did:key:z6Mkmahwm5uBGwZFN1gLbqbgHW4XHSRnyCMgTcntPdN4vpns',
  },
  MERIDIAN: {
    id: 'MERIDIAN',
    name: 'Meridian Bank Travel',
    issuerDid: 'did:key:z6MkqLnXRAv8QX56Y4Mps7qzZLS7HNjLNiA6zn1wffDJUuEZ',
  },
  BARGAIN: {
    id: 'BARGAIN',
    name: 'BargainTrips',
    issuerDid: 'did:key:z6Mkh5qfay6hpNdUF9QkNn6fZ9edj2fHDxkrHwPD54KMWP4p',
  },
} as const

const MERCHANT_ALLOWLIST: readonly PartnerBrand[] = [PARTNERS['AURORA'], PARTNERS['MERIDIAN']] as const
const MERCHANT_TRUSTED_ISSUERS = new Set(MERCHANT_ALLOWLIST.map((brand) => brand.issuerDid))

export function isTrustedIssuer(issuerDid: string): boolean {
  return MERCHANT_TRUSTED_ISSUERS.has(issuerDid)
}

export function findBrandNameForIssuer(issuerDid: string): string | undefined {
  return Object.values(PARTNERS).find((partnerBrand) => partnerBrand.issuerDid === issuerDid)?.name
}
