import { ai } from './genkit'

export type RoomType = 'standard' | 'deluxe' | 'suite'

const ROOM_TYPES: RoomType[] = ['standard', 'deluxe', 'suite']

export const ROOM_RATES: Record<RoomType, number> = {
  standard: 200,
  deluxe: 300,
  suite: 500,
}

const MAX_NIGHTS = 30

export interface Booking {
  nights: number
  roomType: RoomType
}

export interface ParsedRequest extends Booking {
  wantsPartnerDiscount: boolean
}

export function computeSubtotal({ nights, roomType }: Booking): number {
  return ROOM_RATES[roomType] * nights
}

export function describeStay({ nights, roomType }: Booking): string {
  return `${nights} night${nights === 1 ? '' : 's'} in a ${roomType} room`
}

/** Keyword fallback for the discount intent (used only if the LLM is unavailable). */
export function keywordWantsDiscount(text: string): boolean {
  return /\b(discount|voucher|partner|loyalty|rewards)\b/i.test(text)
}

const parsePrompt = ai.prompt('parse-request')

function normalizeRoomType(value: unknown): RoomType {
  const v = String(value ?? '').toLowerCase()
  return (ROOM_TYPES as string[]).includes(v) ? (v as RoomType) : 'standard'
}

function clampNights(value: unknown): number {
  const n = Math.floor(Number(value))
  if (!Number.isFinite(n) || n < 1) return 1
  return Math.min(n, MAX_NIGHTS)
}

export async function parseRequest(userText: string): Promise<ParsedRequest> {
  try {
    const response = await parsePrompt({ userMessage: userText })
    const out = response.output as { wantsPartnerDiscount?: boolean; nights?: number; roomType?: string } | undefined
    if (!out) throw new Error('no structured output')
    return {
      wantsPartnerDiscount: Boolean(out.wantsPartnerDiscount),
      nights: clampNights(out.nights),
      roomType: normalizeRoomType(out.roomType),
    }
  } catch (err) {
    console.warn('[Merchant] request parsing failed; using keyword intent + defaults:', err)
    return { wantsPartnerDiscount: keywordWantsDiscount(userText), nights: 1, roomType: 'standard' }
  }
}
