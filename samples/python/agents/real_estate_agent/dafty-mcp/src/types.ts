import { z } from 'zod';

// Schema for the search_rental_properties tool
export const SearchRentalPropertiesInputSchema = z.object({
  location: z
    .union([z.string(), z.array(z.string())])
    .optional()
    .describe('Location or locations (e.g., Dublin, Cork, specific address) - Defaults to all Ireland if omitted'),
  minPrice: z.number().optional().describe('Minimum price per month'),
  maxPrice: z.number().optional().describe('Maximum price per month'),
  numBeds: z.number().optional().describe('Number of bedrooms (for scraping, 1 means 1-2 beds)'),
  propertyType: z.string().optional().describe('Type of property (e.g., apartment, house)'),
});

// Inferred type from the schema
export type SearchRentalPropertiesParams = z.infer<typeof SearchRentalPropertiesInputSchema>;

// Schema for the get_rental_property_details tool
export const GetRentalPropertyDetailsInputSchema = z.object({
  property_id: z.string().describe('Unique ID of the rental property'),
});

// Inferred type from the schema
export type GetRentalPropertyDetailsParams = z.infer<typeof GetRentalPropertyDetailsInputSchema>;

// Schema for the parse_query tool
export const ParseQueryInputSchema = z.object({
  query: z.string().describe('The natural language query to parse'),
});

// Inferred type from the schema
export type ParseQueryParams = z.infer<typeof ParseQueryInputSchema>;

// Generic interfaces for parsed data
export interface ParsedPriceResult {
  value: number | null;
  type: 'numeric' | 'on_application' | 'unknown';
}

export interface ParsedBedsResult {
  min: number;
  max: number;
  isStudio?: boolean;
}

export interface Unit {
  address: string;
  url: string;
  id: string;
  priceString: string;
  parsedPrice: number | null;
  priceType: 'numeric' | 'on_application' | 'unknown';
  bedsString: string;
  parsedBeds: ParsedBedsResult | null;
  bathsString: string;
  propertyTypeString: string;
  ber?: string;
  tagline: string;
}

export interface Property {
  address: string;
  url: string;
  id: string;
  tagline: string;
  priceString: string;
  parsedPrice: number | null;
  priceType: 'numeric' | 'on_application' | 'unknown';
  bedsString: string;
  parsedBeds: ParsedBedsResult | null;
  bathsString: string;
  propertyTypeString: string;
  ber?: string;
  latitude?: number;
  longitude?: number;
  units?: Property[];
}
