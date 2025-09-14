import * as cheerio from 'cheerio';
import { dublinAreas } from '../data/locations.js';
import type { ParsedPriceResult, ParsedBedsResult } from '../types.js';

// Helper function to parse price strings (e.g., "€2,500 per month", "€500 per week")
export const parsePrice = (priceString: string | undefined): ParsedPriceResult => {
  if (!priceString || typeof priceString !== 'string') return { value: null, type: 'unknown' };

  const priceStrNormalized = priceString.toLowerCase();

  // Check for "Price on Application" or similar non-numeric prices
  if (priceStrNormalized.includes('price on application') || priceStrNormalized.includes('contact agent')) {
    return { value: null, type: 'on_application' };
  }

  // Regex to capture amount and an optional period (month/week), including variations like "p/m", "p/w"
  const match = priceStrNormalized.match(
    /(?:€\s*)?([\d,]+(?:\.\d{2})?)\s*(?:(?:per\s*)?(month|week|mth|wk|pm|p\/m|pw|p\/w|perweek))?/i
  );

  if (match && match[1]) {
    // If we at least found a number that looks like an amount
    let amount = parseFloat(match[1].replace(/,/g, ''));
    if (isNaN(amount)) return { value: null, type: 'unknown' };

    const periodWord = match[2] ? match[2].toLowerCase() : undefined;

    if (periodWord) {
      // If a period was explicitly found
      if (
        periodWord.startsWith('week') ||
        periodWord.startsWith('wk') ||
        periodWord === 'pw' ||
        periodWord === 'p/w' ||
        periodWord === 'perweek'
      ) {
        amount = Math.round((amount * 52) / 12); // Convert weekly to monthly
      }
      // Otherwise, assume monthly (includes 'month', 'mth', 'pm', 'p/m')
      return { value: amount, type: 'numeric' };
    } else if (priceStrNormalized.includes('€')) {
      // No explicit period, but has '€', assume it's a direct (likely monthly) price
      return { value: amount, type: 'numeric' };
    }
    // If no period and no euro symbol, it's ambiguous, fall through to stricter checks or return null
  }

  // Fallback for simple numbers that might be prices but didn't match the main regex structure
  // (e.g. "1500 per month" where "per month" wasn't captured by the optional group logic if it's too far)
  // This section needs to be careful not to misinterpret address numbers.
  const stricterMatchForStandaloneNumbers = priceStrNormalized.match(
    /^([\d,]+(?:\.\d{2})?)\s*(?:per\s*)?(month|week|mth|wk|pm|p\/m|pw|p\/w|perweek)$/i
  );
  if (stricterMatchForStandaloneNumbers && stricterMatchForStandaloneNumbers[1]) {
    let amount = parseFloat(stricterMatchForStandaloneNumbers[1].replace(/,/g, ''));
    if (isNaN(amount)) return { value: null, type: 'unknown' };
    const periodWord = stricterMatchForStandaloneNumbers[2]
      ? stricterMatchForStandaloneNumbers[2].toLowerCase()
      : 'month';
    if (
      periodWord.startsWith('week') ||
      periodWord.startsWith('wk') ||
      periodWord === 'pw' ||
      periodWord === 'p/w' ||
      periodWord === 'perweek'
    ) {
      amount = Math.round((amount * 52) / 12);
    }
    return { value: amount, type: 'numeric' };
  }

  // Final check for very simple numeric strings that might be prices if they are large enough
  // or if they were missed by above logic but are clearly prices.
  const simpleNumericOnly = priceString.replace(/[^0-9.]/g, '');
  if (simpleNumericOnly.length > 0 && simpleNumericOnly === priceString.replace(/[^0-9€\s.,]/g, '')) {
    const potentialPrice = parseFloat(simpleNumericOnly);
    if (!isNaN(potentialPrice)) {
      if (
        priceStrNormalized.includes('€') ||
        priceStrNormalized.includes('per month') ||
        priceStrNormalized.includes('per week')
      ) {
        if (priceStrNormalized.includes('€')) {
          return { value: potentialPrice, type: 'numeric' };
        }
      }
      if (
        priceStrNormalized.toLowerCase().includes('dublin') &&
        priceStrNormalized.includes(potentialPrice.toString()) &&
        potentialPrice < 100
      ) {
        return { value: null, type: 'unknown' };
      }
      if (
        potentialPrice < 100 &&
        !priceStrNormalized.includes('€') &&
        !priceStrNormalized.match(/(month|week|mth|wk|pm|pw|p\/m|p\/w)/i)
      ) {
        return { value: null, type: 'unknown' }; // Small number, no indicators
      }
      if (potentialPrice >= 100) {
        return { value: potentialPrice, type: 'numeric' }; // Allow larger numbers if they are purely numeric
      }
    }
  }

  return { value: null, type: 'unknown' };
};

// Helper function to parse bed strings (e.g., "1 Bed", "2 Beds", "Studio")
// Returns an object { min: number, max: number } or null
export const parseBeds = (bedString: string | undefined): ParsedBedsResult | null => {
  if (!bedString || typeof bedString !== 'string') return null;

  const bedStrNormalized = bedString.toLowerCase();

  if (bedStrNormalized.includes('studio')) {
    return { min: 1, max: 1, isStudio: true };
  }

  const rangeMatch = bedStrNormalized.match(/(\d+)\s*(?:to|-)\s*(\d+)\s*bed/i);
  if (rangeMatch && rangeMatch[1] && rangeMatch[2]) {
    const minBeds = parseInt(rangeMatch[1], 10);
    const maxBeds = parseInt(rangeMatch[2], 10);
    if (!isNaN(minBeds) && !isNaN(maxBeds)) {
      return { min: Math.min(minBeds, maxBeds), max: Math.max(minBeds, maxBeds) };
    }
  }

  const singleMatch = bedStrNormalized.match(/(\d+)\s*bed/i);
  if (singleMatch && singleMatch[1]) {
    const num = parseInt(singleMatch[1], 10);
    if (!isNaN(num)) {
      return { min: num, max: num };
    }
  }
  return null;
};

export const extractLatLng = (html: string, selector: string): { lat: number; lng: number } | null => {
  const $ = cheerio.load(html);
  const link = $(selector).attr('href');

  if (link) {
    const match = link.match(/q=loc:([\d.-]+)\+([\d.-]+)/) || link.match(/viewpoint=([\d.-]+),([\d.-]+)/);
    if (match && match[1] && match[2]) {
      const lat = parseFloat(match[1]);
      const lng = parseFloat(match[2]);
      if (!isNaN(lat) && !isNaN(lng)) {
        return { lat, lng };
      }
    }
  }

  return null;
};

export const slugify = (str: string): string => {
  if (typeof str !== 'string') return '';
  return str
    .trim()
    .toLowerCase()
    .replace(/\s+/g, '-')
    .replace(/[^a-z0-9-]/g, '');
};

export const formatBer = (ber: string | undefined): string | undefined => {
  if (!ber) return undefined;
  const cleanedBer = ber.replace('BER ', '').trim();
  if (cleanedBer === 'SI_666') {
    return 'Exempt';
  }
  return cleanedBer;
};

export const generateDaftLocationSlug = (locationString: string): string => {
  if (typeof locationString !== 'string' || locationString.trim() === '') {
    return '';
  }

  const parts = locationString
    .split(',')
    .map((p) => slugify(p.trim()))
    .filter((p) => p);

  if (parts.length === 2) {
    // Handles "Carrigaline, Cork" -> "carrigaline-cork"
    return parts.join('-');
  }

  const singlePartSlug = slugify(locationString);

  // Handles "Dublin 2" -> "dublin-2-dublin"
  if (/^dublin-\d+$/.test(singlePartSlug)) {
    return `${singlePartSlug}-dublin`;
  }

  // Handles areas within Dublin like "Sandymount" -> "sandymount-dublin"
  if (dublinAreas.includes(singlePartSlug)) {
    return `${singlePartSlug}-dublin`;
  }

  // Default for single names like "cork" or "galway"
  return singlePartSlug;
};
