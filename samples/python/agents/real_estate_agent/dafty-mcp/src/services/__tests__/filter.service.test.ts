import { describe, it, expect } from 'vitest';
import { filterProperties } from '../filter.service.js';
import type { Property } from '../../types.js';

const mockProperties: Property[] = [
  {
    id: '1',
    address: '123 Main St, Dublin 4',
    url: '/1',
    tagline: 'A nice apartment',
    priceString: '€2,000 per month',
    bedsString: '2 beds',
    bathsString: '2 baths',
    propertyTypeString: 'Apartment',
    parsedPrice: 2000,
    priceType: 'numeric',
    parsedBeds: { min: 2, max: 2 },
  },
  {
    id: '2',
    address: '456 Oak Ave, Dublin 2',
    url: '/2',
    tagline: 'A cozy studio',
    priceString: '€1,500 per month',
    bedsString: '1 bed',
    bathsString: '1 bath',
    propertyTypeString: 'Studio',
    parsedPrice: 1500,
    priceType: 'numeric',
    parsedBeds: { min: 1, max: 1 },
  },
  {
    id: '3',
    address: '789 Pine Ln, Ringsend, Dublin 4',
    url: '/3',
    tagline: 'A spacious house',
    priceString: '€2,500 per month',
    bedsString: '3 beds',
    bathsString: '3 baths',
    propertyTypeString: 'House',
    parsedPrice: 2500,
    priceType: 'numeric',
    parsedBeds: { min: 3, max: 3 },
  },
  {
    id: '4',
    address: '101 Maple Dr, Grand Canal Dock, D4',
    url: '/4',
    tagline: 'A modern apartment',
    priceString: 'Price on Application',
    bedsString: 'Studio',
    bathsString: '1 bath',
    propertyTypeString: 'Apartment',
    parsedPrice: null,
    priceType: 'on_application',
    parsedBeds: { min: 0, max: 0, isStudio: true },
  },
  {
    id: '5',
    address: '210 Birch Rd, Cork City',
    url: '/5',
    tagline: 'A great apartment',
    priceString: '€1,200 per month',
    bedsString: '2 beds',
    bathsString: '1 bath',
    propertyTypeString: 'Apartment',
    parsedPrice: 1200,
    priceType: 'numeric',
    parsedBeds: { min: 2, max: 2 },
  },
];

describe('Filter Service', () => {
  describe('filterProperties', () => {
    it('should filter by min and max price', () => {
      const filtered = filterProperties(mockProperties, { minPrice: 1800, maxPrice: 2200 });
      expect(filtered).toHaveLength(1);
      expect(filtered[0].id).toBe('1');
    });

    it('should filter by number of beds', () => {
      const filtered = filterProperties(mockProperties, { numBeds: 1 });
      expect(filtered).toHaveLength(1);
      expect(filtered[0].id).toBe('2');
    });

    it('should filter by property type', () => {
      const filtered = filterProperties(mockProperties, { propertyType: 'House' });
      expect(filtered).toHaveLength(1);
      expect(filtered[0].id).toBe('3');
    });

    it('should filter by a single location string', () => {
      const filtered = filterProperties(mockProperties, { location: 'Dublin 2' });
      expect(filtered).toHaveLength(1);
      expect(filtered[0].id).toBe('2');
    });

    it('should filter by an array of locations', () => {
      const filtered = filterProperties(mockProperties, { location: ['Cork City', 'Dublin 2'] });
      expect(filtered).toHaveLength(2);
      expect(filtered.map((p) => p.id)).toEqual(['2', '5']);
    });

    it('should handle Ringsend location synonyms', () => {
      const filtered = filterProperties(mockProperties, { location: 'Ringsend' });
      expect(filtered).toHaveLength(2);
      expect(filtered.map((p) => p.id)).toEqual(['3', '4']);
    });

    it('should handle postal code matching (e.g., "Dublin 4" and "D4")', () => {
      const filtered = filterProperties(mockProperties, { location: 'Dublin 4' });
      expect(filtered).toHaveLength(3);
      expect(filtered.map((p) => p.id)).toEqual(['1', '3', '4']);
    });

    it('should return an empty array if no properties match', () => {
      const filtered = filterProperties(mockProperties, { minPrice: 3000 });
      expect(filtered).toHaveLength(0);
    });

    it('should not filter if a property has no address when filtering by location', () => {
      const propertiesWithNoAddress = [
        ...mockProperties,
        {
          id: '6',
          address: null,
          url: '/6',
          tagline: '',
          priceString: '',
          bedsString: '',
          bathsString: '',
          propertyTypeString: '',
          parsedPrice: null,
          priceType: 'unknown',
          parsedBeds: null,
        } as unknown as Property,
      ];
      const filtered = filterProperties(propertiesWithNoAddress, { location: 'Dublin' });
      expect(filtered.find((p) => p.id === '6')).toBeUndefined();
    });

    it('should correctly combine multiple filters', () => {
      const filtered = filterProperties(mockProperties, {
        location: 'Dublin 4',
        minPrice: 2400,
        propertyType: 'House',
      });
      expect(filtered).toHaveLength(1);
      expect(filtered[0].id).toBe('3');
    });

    it('should not filter if a property has no bed data when filtering by beds', () => {
      const propertiesWithNoBedData = [
        ...mockProperties,
        {
          id: '7',
          address: 'Some Address',
          url: '/7',
          tagline: '',
          priceString: '€1000',
          bedsString: '',
          bathsString: '',
          propertyTypeString: '',
          parsedPrice: 1000,
          priceType: 'numeric',
          parsedBeds: null,
        } as Property,
      ];
      const filtered = filterProperties(propertiesWithNoBedData, { numBeds: 2 });
      expect(filtered.find((p) => p.id === '7')).toBeUndefined();
    });

    it('should not filter if a property has no property type when filtering by type', () => {
      const propertiesWithNoType = [
        ...mockProperties,
        {
          id: '8',
          address: 'Some Address',
          url: '/8',
          tagline: '',
          priceString: '€1000',
          bedsString: '1 bed',
          bathsString: '1 bath',
          propertyTypeString: null,
          parsedPrice: 1000,
          priceType: 'numeric',
          parsedBeds: { min: 1, max: 1 },
        } as unknown as Property,
      ];
      const filtered = filterProperties(propertiesWithNoType, { propertyType: 'Apartment' });
      expect(filtered.find((p) => p.id === '8')).toBeUndefined();
    });
  });
});