import type { Property, SearchRentalPropertiesParams } from '../types.js';

/**
 * Filters an array of properties based on the provided search criteria.
 * @param properties The array of properties to filter.
 * @param filters The search criteria.
 * @returns A filtered array of properties.
 */
export function filterProperties(properties: Property[], filters: SearchRentalPropertiesParams): Property[] {
  return properties.filter((p) => {
    // Price filter
    if (filters.minPrice !== undefined || filters.maxPrice !== undefined) {
      if (p.priceType !== 'numeric' || p.parsedPrice === null) return false;
      if (filters.minPrice !== undefined && p.parsedPrice < filters.minPrice) return false;
      if (filters.maxPrice !== undefined && p.parsedPrice > filters.maxPrice) return false;
    }

    // Number of beds filter
    if (filters.numBeds !== undefined) {
      if (p.parsedBeds === null || p.parsedBeds.min === undefined || p.parsedBeds.max === undefined) {
        return false;
      }
      if (filters.numBeds < p.parsedBeds.min || filters.numBeds > p.parsedBeds.max) {
        return false;
      }
    }

    // Property type filter
    if (filters.propertyType) {
      if (!p.propertyTypeString) return false;
      if (!p.propertyTypeString.toLowerCase().includes(filters.propertyType.toLowerCase())) return false;
    }

    // Location filter
    if (filters.location) {
      const requestedLocations = (Array.isArray(filters.location) ? filters.location : [filters.location])
        .map((l) => l.toLowerCase().trim())
        .filter((l) => l !== '');

      if (requestedLocations.length > 0) {
        const propertyAddressLower = p.address ? p.address.toLowerCase() : '';
        if (!propertyAddressLower) return false;

        const locationMatchFound = requestedLocations.some((requestedLocationLower) => {
          if (requestedLocationLower === 'ringsend') {
            const ringsendSynonyms = ['ringsend', 'irishtown', 'grand canal dock'];
            return ringsendSynonyms.some((term) => propertyAddressLower.includes(term));
          }

          if (propertyAddressLower.includes(requestedLocationLower)) return true;

          const postalCodeMatch = requestedLocationLower.match(/dublin\s*(\d+)/i);
          if (postalCodeMatch && postalCodeMatch[1]) {
            const postalCodeFull = `dublin ${postalCodeMatch[1]}`;
            const postalCodeShort = `d${postalCodeMatch[1]}`;
            return (
              propertyAddressLower.includes(postalCodeFull) ||
              propertyAddressLower.match(new RegExp(`\\b${postalCodeShort}\\b`, 'i'))
            );
          }
          return false;
        });

        if (!locationMatchFound) return false;
      }
    }

    return true;
  });
}