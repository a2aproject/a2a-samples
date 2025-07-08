import { describe, it, expect } from 'vitest';
import { parsePrice, parseBeds, slugify, extractLatLng } from '../utils/parser.utils.js';

describe('daftScraper helpers', () => {
  describe('extractLatLng', () => {
    it('should extract lat and long from satellite view link', () => {
      const html = `<div class="sc-eb305aa9-39 fhfxAx"><h3 class="sc-eb305aa9-6 sc-eb305aa9-37 KkiWU fCUHAZ">Map</h3><div class="sc-eb305aa9-35 jfAOAq"><div class="sc-d17e3613-6 jUPFjn button-container"><a aria-label="Satellite View" href="https://www.google.com/maps?t=k&q=loc:53.292643842768456+-6.1705297173718066" data-tracking="LaunchSatellite" data-testid="satelite-button" target="_blank" rel="noreferrer noopener" class="sc-d17e3613-5 dTSeGm"><div visibility="visible" class="sc-d17e3613-0 peOLg"><div data-testid="" class="sc-d17e3613-3 kDuilh"><svg viewBox="0 0 24 24" width="1em" height="1em"><g fill="none" fill-rule="evenodd" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"><path d="M21.5 12v7.917c0 .874-.71 1.583-1.583 1.583H4.083c-.874 0-1.583-.71-1.583-1.583V4.083c0-.874.71-1.583 1.583-1.583H12M15.5 2.5h6v6M10.5 13.5l11-11"></path></g></svg></div> <span class="sc-d17e3613-1 iTzdLu">Satellite View</span></div></a></div><div class="sc-d17e3613-6 jUPFjn button-container"><a aria-label="Street View" href="https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=53.292643842768456,-6.1705297173718066" data-tracking="LaunchStreet" data-testid="streetview-button" target="_blank" rel="noreferrer noopener" class="sc-d17e3613-5 dTSeGm"><div visibility="visible" class="sc-d17e3613-0 peOLg"><div data-testid="" class="sc-d17e3613-3 kDuilh"><svg viewBox="0 0 24 24" width="1em" height="1em"><g fill="none" fill-rule="evenodd" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"><path d="M21.5 12v7.917c0 .874-.71 1.583-1.583 1.583H4.083c-.874 0-1.583-.71-1.583-1.583V4.083c0-.874.71-1.583 1.583-1.583H12M15.5 2.5h6v6M10.5 13.5l11-11"></path></g></svg></div> <span class="sc-d17e3613-1 iTzdLu">Street View</span></div></a></div></div></div>`;
      expect(extractLatLng(html, 'a[data-testid="satelite-button"]')).toEqual({
        lat: 53.292643842768456,
        lng: -6.1705297173718066,
      });
    });

    it('should extract lat and long from street view link', () => {
      const html = `<div class="sc-eb305aa9-39 fhfxAx"><h3 class="sc-eb305aa9-6 sc-eb305aa9-37 KkiWU fCUHAZ">Map</h3><div class="sc-eb305aa9-35 jfAOAq"><div class="sc-d17e3613-6 jUPFjn button-container"><a aria-label="Satellite View" href="https://www.google.com/maps?t=k&q=loc:53.292643842768456+-6.1705297173718066" data-tracking="LaunchSatellite" data-testid="satelite-button" target="_blank" rel="noreferrer noopener" class="sc-d17e3613-5 dTSeGm"><div visibility="visible" class="sc-d17e3613-0 peOLg"><div data-testid="" class="sc-d17e3613-3 kDuilh"><svg viewBox="0 0 24 24" width="1em" height="1em"><g fill="none" fill-rule="evenodd" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"><path d="M21.5 12v7.917c0 .874-.71 1.583-1.583 1.583H4.083c-.874 0-1.583-.71-1.583-1.583V4.083c0-.874.71-1.583 1.583-1.583H12M15.5 2.5h6v6M10.5 13.5l11-11"></path></g></svg></div> <span class="sc-d17e3613-1 iTzdLu">Satellite View</span></div></a></div><div class="sc-d17e3613-6 jUPFjn button-container"><a aria-label="Street View" href="https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=53.292643842768456,-6.1705297173718066" data-tracking="LaunchStreet" data-testid="streetview-button" target="_blank" rel="noreferrer noopener" class="sc-d17e3613-5 dTSeGm"><div visibility="visible" class="sc-d17e3613-0 peOLg"><div data-testid="" class="sc-d17e3613-3 kDuilh"><svg viewBox="0 0 24 24" width="1em" height="1em"><g fill="none" fill-rule="evenodd" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"><path d="M21.5 12v7.917c0 .874-.71 1.583-1.583 1.583H4.083c-.874 0-1.583-.71-1.583-1.583V4.083c0-.874.71-1.583 1.583-1.583H12M15.5 2.5h6v6M10.5 13.5l11-11"></path></g></svg></div> <span class="sc-d17e3613-1 iTzdLu">Street View</span></div></a></div></div></div>`;
      expect(extractLatLng(html, 'a[data-testid="streetview-button"]')).toEqual({
        lat: 53.292643842768456,
        lng: -6.1705297173718066,
      });
    });

    it('should return null if link is not found', () => {
      const html = `<div></div>`;
      expect(extractLatLng(html, 'a')).toBeNull();
    });

    it('should return null if href is missing', () => {
      const html = `<a></a>`;
      expect(extractLatLng(html, 'a')).toBeNull();
    });

    it('should return null if lat/lng are not in the href', () => {
      const html = `<a href="https://www.google.com/maps"></a>`;
      expect(extractLatLng(html, 'a')).toBeNull();
    });
  });
  describe('parsePrice', () => {
    it('should parse valid monthly price strings', () => {
      expect(parsePrice('€2,500 per month')).toEqual({ value: 2500, type: 'numeric' });
      expect(parsePrice('€1,000 p/m')).toEqual({ value: 1000, type: 'numeric' });
      expect(parsePrice('€800pm')).toEqual({ value: 800, type: 'numeric' });
      expect(parsePrice('€ 750 per month')).toEqual({ value: 750, type: 'numeric' });
      expect(parsePrice('€750 Per Month')).toEqual({ value: 750, type: 'numeric' });
    });

    it('should parse valid weekly price strings and convert to monthly', () => {
      expect(parsePrice('€500 per week')).toEqual({ value: Math.round((500 * 52) / 12), type: 'numeric' });
      expect(parsePrice('€200 p/w')).toEqual({ value: Math.round((200 * 52) / 12), type: 'numeric' });
      expect(parsePrice('€100pw')).toEqual({ value: Math.round((100 * 52) / 12), type: 'numeric' });
    });

    it('should handle price strings with only numbers if € or per is present', () => {
      expect(parsePrice('€2000')).toEqual({ value: 2000, type: 'numeric' });
      expect(parsePrice('1500 per month')).toEqual({ value: 1500, type: 'numeric' });
    });

    it('should return type "on_application" for "Price on Application"', () => {
      expect(parsePrice('Price on Application')).toEqual({ value: null, type: 'on_application' });
      expect(parsePrice('Contact Agent')).toEqual({ value: null, type: 'on_application' });
    });

    it('should return type "unknown" for invalid or ambiguous price strings', () => {
      expect(parsePrice('Not a price')).toEqual({ value: null, type: 'unknown' });
      expect(parsePrice('')).toEqual({ value: null, type: 'unknown' });
      expect(parsePrice(undefined)).toEqual({ value: null, type: 'unknown' });
      expect(parsePrice('€')).toEqual({ value: null, type: 'unknown' });
      expect(parsePrice('per month')).toEqual({ value: null, type: 'unknown' });
      expect(parsePrice('Dublin 4')).toEqual({ value: null, type: 'unknown' });
      expect(parsePrice('5')).toEqual({ value: null, type: 'unknown' });
      expect(parsePrice('D4')).toEqual({ value: null, type: 'unknown' });
    });

    it('should handle price strings with decimals', () => {
      expect(parsePrice('€2500.50 per month')).toEqual({ value: 2500.5, type: 'numeric' });
      expect(parsePrice('€500.75 per week')).toEqual({ value: Math.round((500.75 * 52) / 12), type: 'numeric' });
    });

    it('should handle price strings with no spaces', () => {
      expect(parsePrice('€2000permonth')).toEqual({ value: 2000, type: 'numeric' });
      expect(parsePrice('€100perweek')).toEqual({ value: Math.round((100 * 52) / 12), type: 'numeric' });
    });

    it('should correctly parse numbers that could be postal codes if context is missing', () => {
      expect(parsePrice('50000')).toEqual({ value: 50000, type: 'numeric' });
      expect(parsePrice('€50')).toEqual({ value: 50, type: 'numeric' });
      expect(parsePrice('50 per month')).toEqual({ value: 50, type: 'numeric' });
      expect(parsePrice('50 p/w')).toEqual({ value: Math.round((50 * 52) / 12), type: 'numeric' });
    });
  });

  describe('parseBeds', () => {
    it('should parse valid single bed strings', () => {
      expect(parseBeds('1 Bed')).toEqual({ min: 1, max: 1 });
      expect(parseBeds('2 Beds')).toEqual({ min: 2, max: 2 });
      expect(parseBeds('5 bed')).toEqual({ min: 5, max: 5 });
    });

    it('should parse "Studio" as 1 bed and mark as studio', () => {
      expect(parseBeds('Studio Apartment')).toEqual({ min: 1, max: 1, isStudio: true });
      expect(parseBeds('Studio')).toEqual({ min: 1, max: 1, isStudio: true });
    });

    it('should parse valid bed range strings', () => {
      expect(parseBeds('1-2 Beds')).toEqual({ min: 1, max: 2 });
      expect(parseBeds('2 - 3 beds')).toEqual({ min: 2, max: 3 });
      expect(parseBeds('1 to 4 Bed')).toEqual({ min: 1, max: 4 });
    });

    it('should return null for invalid bed strings', () => {
      expect(parseBeds('No Beds')).toBeNull();
      expect(parseBeds('Beds: Many')).toBeNull();
      expect(parseBeds('')).toBeNull();
      expect(parseBeds(undefined)).toBeNull();
      expect(parseBeds('Apartment')).toBeNull();
    });

    it('should handle variations in casing and spacing', () => {
      expect(parseBeds('3 bEdS')).toEqual({ min: 3, max: 3 });
      expect(parseBeds(' 4   bed ')).toEqual({ min: 4, max: 4 });
    });
  });

  describe('slugify', () => {
    it('should convert to lowercase and replace spaces with hyphens', () => {
      expect(slugify('Dublin City Centre')).toBe('dublin-city-centre');
    });

    it('should remove special characters except hyphens', () => {
      expect(slugify('Ringsend, Dublin 4!')).toBe('ringsend-dublin-4');
    });

    it('should handle multiple spaces correctly', () => {
      expect(slugify('Cork  County')).toBe('cork-county');
    });

    it('should handle leading/trailing spaces', () => {
      expect(slugify('  Galway ')).toBe('galway');
    });

    it('should return an empty string for empty input', () => {
      expect(slugify('')).toBe('');
    });

    it('should handle strings that are already slugs', () => {
      expect(slugify('already-a-slug')).toBe('already-a-slug');
    });

    it('should handle numbers in strings', () => {
      expect(slugify('Dublin 18')).toBe('dublin-18');
    });

    it('should handle mixed case input', () => {
      expect(slugify('CoRk CiTy')).toBe('cork-city');
    });

    it('should return empty string for non-string input', () => {
      // @ts-expect-error Testing invalid input
      expect(slugify(undefined)).toBe('');
      // @ts-expect-error Testing invalid input
      expect(slugify(null)).toBe('');
      // @ts-expect-error Testing invalid input
      expect(slugify(123)).toBe('');
    });
  });
});
