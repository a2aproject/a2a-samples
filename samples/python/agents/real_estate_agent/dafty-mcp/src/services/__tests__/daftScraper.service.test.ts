import { describe, it, expect, vi, beforeEach } from 'vitest';
import { handleSearchRentalPropertiesScraping } from '../daftScraper.service.js';
import * as fetchService from '../fetch.service.js';
import * as parserService from '../parser.service.js';
import * as filterService from '../filter.service.js';
import { ScraperError } from '../../errors.js';
import type { Property } from '../../types.js';

vi.mock('../fetch.service.js');
vi.mock('../parser.service.js');
vi.mock('../filter.service.js');
vi.mock('../utils/parser.utils.js', () => ({
  slugify: (s: string) => s.toLowerCase(),
  generateDaftLocationSlug: (s: string) => s.toLowerCase().replace(' ', '-'),
}));

describe('Daft Scraper Service', () => {
  const mockProperty: Property = {
    id: '1',
    address: '123 Main St',
    url: 'http://example.com/1',
    priceString: '€1,000 per month',
    parsedPrice: 1000,
    priceType: 'numeric',
    bedsString: '1 Bed',
    parsedBeds: { min: 1, max: 1 },
    bathsString: '1 Bath',
    propertyTypeString: 'Apartment',
    tagline: 'A nice place',
  };

  beforeEach(() => {
    vi.resetAllMocks();
  });

  describe('handleSearchRentalPropertiesScraping', () => {
    it('should orchestrate scraping and filtering to return properties', async () => {
      vi.spyOn(fetchService, 'fetchPageHTML').mockResolvedValue('<html></html>');
      vi.spyOn(parserService, 'getTotalPages').mockReturnValue(1);
      vi.spyOn(parserService, 'parseSearchResults').mockReturnValue([{ ...mockProperty }]);
      vi.spyOn(parserService, 'parsePropertyDetails').mockReturnValue({ ...mockProperty });
      vi.spyOn(filterService, 'filterProperties').mockReturnValue([{ ...mockProperty }]);

      const result = await handleSearchRentalPropertiesScraping({ location: 'Dublin' });

      expect(result.isError).toBeUndefined();
      expect(JSON.parse(result.content[0].text)).toEqual([{ ...mockProperty }]);
      expect(fetchService.fetchPageHTML).toHaveBeenCalled();
      expect(parserService.parseSearchResults).toHaveBeenCalled();
      expect(filterService.filterProperties).toHaveBeenCalled();
    });

    it('should handle multi-page scraping', async () => {
      const fetchSpy = vi.spyOn(fetchService, 'fetchPageHTML').mockResolvedValue('<html></html>');
      vi.spyOn(parserService, 'getTotalPages').mockReturnValue(2); // 2 pages
      const searchResultsSpy = vi
        .spyOn(parserService, 'parseSearchResults')
        .mockReturnValueOnce([{ ...mockProperty, url: undefined }]) // No URL, so no detail fetch
        .mockReturnValueOnce([]); // Second page is empty
      vi.spyOn(filterService, 'filterProperties').mockImplementation((props) => props);

      await handleSearchRentalPropertiesScraping({ location: 'Dublin' });

      expect(fetchSpy).toHaveBeenCalledTimes(2); // Page 1, Page 2
      expect(searchResultsSpy).toHaveBeenCalledTimes(2);
    });

    it('should handle properties with multiple units', async () => {
      const propertyWithUnits = {
        ...mockProperty,
        units: [
          { ...mockProperty, id: '1a' },
          { ...mockProperty, id: '1b' },
        ],
      };
      vi.spyOn(fetchService, 'fetchPageHTML').mockResolvedValue('<html></html>');
      vi.spyOn(parserService, 'getTotalPages').mockReturnValue(1);
      vi.spyOn(parserService, 'parseSearchResults').mockReturnValue([{ ...mockProperty }]);
      vi.spyOn(parserService, 'parsePropertyDetails').mockReturnValue(propertyWithUnits);
      vi.spyOn(filterService, 'filterProperties').mockImplementation((props) => props); // Pass through

      const result = await handleSearchRentalPropertiesScraping({ location: 'Dublin' });
      const parsedResult = JSON.parse(result.content[0].text);

      expect(parsedResult).toHaveLength(2);
      expect(parsedResult.map((p: Property) => p.id)).toEqual(['1a', '1b']);
    });

    it('should throw a ScraperError if any underlying service fails', async () => {
      vi.spyOn(fetchService, 'fetchPageHTML').mockRejectedValue(new Error('Network Error'));
      await expect(handleSearchRentalPropertiesScraping({ location: 'Dublin' })).rejects.toThrow(ScraperError);
    });

    it('should handle non-Error exceptions', async () => {
      vi.spyOn(fetchService, 'fetchPageHTML').mockRejectedValue('a string error');
      await expect(handleSearchRentalPropertiesScraping({ location: 'Dublin' })).rejects.toThrow(
        'An unknown error occurred during scraping.'
      );
    });
  });

  describe('buildSearchUrl', () => {
    it('should handle multiple locations', async () => {
      vi.spyOn(fetchService, 'fetchPageHTML').mockResolvedValue('<html></html>');
      vi.spyOn(parserService, 'getTotalPages').mockReturnValue(1);
      vi.spyOn(parserService, 'parseSearchResults').mockReturnValue([]);
      await handleSearchRentalPropertiesScraping({ location: ['Dublin', 'Cork'] });
      expect(fetchService.fetchPageHTML).toHaveBeenCalledWith(
        expect.stringContaining('location=dublin&location=cork'),
        expect.any(Number)
      );
    });

    it('should handle different property types', async () => {
      vi.spyOn(fetchService, 'fetchPageHTML').mockResolvedValue('<html></html>');
      vi.spyOn(parserService, 'getTotalPages').mockReturnValue(1);
      vi.spyOn(parserService, 'parseSearchResults').mockReturnValue([]);
      await handleSearchRentalPropertiesScraping({ propertyType: 'House' });
      expect(fetchService.fetchPageHTML).toHaveBeenCalledWith(expect.stringContaining('/houses'), expect.any(Number));

      await handleSearchRentalPropertiesScraping({ propertyType: 'Apartment' });
      expect(fetchService.fetchPageHTML).toHaveBeenCalledWith(
        expect.stringContaining('/apartments'),
        expect.any(Number)
      );

      await handleSearchRentalPropertiesScraping({ propertyType: 'Studio' });
      expect(fetchService.fetchPageHTML).toHaveBeenCalledWith(expect.stringContaining('/studios'), expect.any(Number));
    });

    it('should handle number of beds', async () => {
      vi.spyOn(fetchService, 'fetchPageHTML').mockResolvedValue('<html></html>');
      vi.spyOn(parserService, 'getTotalPages').mockReturnValue(1);
      vi.spyOn(parserService, 'parseSearchResults').mockReturnValue([]);
      await handleSearchRentalPropertiesScraping({ numBeds: 3 });
      expect(fetchService.fetchPageHTML).toHaveBeenCalledWith(
        expect.stringContaining('numBeds_from=3&numBeds_to=3'),
        expect.any(Number)
      );
    });

    it('should handle price range', async () => {
      vi.spyOn(fetchService, 'fetchPageHTML').mockResolvedValue('<html></html>');
      vi.spyOn(parserService, 'getTotalPages').mockReturnValue(1);
      vi.spyOn(parserService, 'parseSearchResults').mockReturnValue([]);
      await handleSearchRentalPropertiesScraping({ minPrice: 1000, maxPrice: 2000 });
      expect(fetchService.fetchPageHTML).toHaveBeenCalledWith(
        expect.stringContaining('rentalPrice_from=1000&rentalPrice_to=2000'),
        expect.any(Number)
      );
    });

    it('should construct correct multi-page URL when base URL has no query params', async () => {
      const fetchSpy = vi.spyOn(fetchService, 'fetchPageHTML').mockResolvedValue('<html></html>');
      vi.spyOn(parserService, 'getTotalPages').mockReturnValue(2);
      vi.spyOn(parserService, 'parseSearchResults').mockReturnValue([]);
      await handleSearchRentalPropertiesScraping({}); // No params
      expect(fetchSpy).toHaveBeenCalledWith(expect.stringContaining('?page=2'), 2);
    });
  });
});