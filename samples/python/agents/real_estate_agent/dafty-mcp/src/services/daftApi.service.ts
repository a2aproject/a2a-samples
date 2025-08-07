// ==========================================================================================
// IMPORTANT DISCLAIMER:
// The Daft.ie API (v3) used by the `get_rental_property_details` tool in this file
// requires an API key for authentication. This key is typically not available for
// public or general developer use.
//
// To inquire about API access, refer to the official Daft.ie API documentation:
// https://api.daft.ie/doc/v3/#using
//
// Without a valid API key (set as the DAFT_API_KEY environment variable),
// the `get_rental_property_details` tool WILL LIKELY FAIL with authorization errors (e.g., 401/403).
// The scraping-based `search_rental_properties` tool does NOT rely on this API key.
// ==========================================================================================
import axios from 'axios';
import type { TextContent } from '@modelcontextprotocol/sdk/types.js';
import type { GetRentalPropertyDetailsParams } from '../types.js';
import { config } from '../config.js';
import logger from '../logger.js';
import { ApiError } from '../errors.js';

// Create axios instance for Daft.ie API
// IMPORTANT: The Daft.ie v3 API likely requires an API key for most (if not all) operations.
// Without a valid key (set via DAFT_API_KEY environment variable), requests will likely fail (e.g., 403 Forbidden).
// This functionality is likely disabled for general use as API keys are typically restricted.
export const daftApi = axios.create({
  baseURL: config.daft.apiBaseUrl,
  headers: {
    'Content-Type': 'application/json',
    // Authorization header will be added dynamically if DAFT_API_KEY is present
  },
});

// Add Authorization header if API key is provided
if (config.daft.apiKey) {
  daftApi.defaults.headers.common['Authorization'] = `Bearer ${config.daft.apiKey}`;
  logger.info('[daftApi.service.ts] DAFT_API_KEY found, Authorization header will be used for API calls.');
} else {
  logger.info('[daftApi.service.ts] DAFT_API_KEY not found. API calls may be unauthorized and fail.');
}

export async function handleGetRentalPropertyDetailsApi({
  property_id,
}: GetRentalPropertyDetailsParams): Promise<{ content: TextContent[]; isError?: boolean }> {
  logger.info(`--- daftApi.service.ts: handleGetRentalPropertyDetailsApi CALLED for ID: ${property_id} ---`);
  try {
    // This endpoint is a placeholder from the original code.
    // Consult Daft.ie API docs for the actual details endpoint if using the API.
    const response = await daftApi.get(`/listings/${property_id}`);
    logger.info(`[daftApi.service.ts] API call for property ID ${property_id} successful. Status: ${response.status}`);
    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify(response.data, null, 2),
        },
      ],
    };
  } catch (error) {
    let errorMessage = `Error fetching details for property ID "${property_id}" from Daft.ie API`;
    if (axios.isAxiosError(error)) {
      errorMessage = `Daft.ie API error for property ID "${property_id}": ${error.response?.data?.message || error.message}. Status: ${error.response?.status}`;
    } else if (error instanceof Error) {
      errorMessage = `Generic error for property ID "${property_id}" using Daft.ie API: ${error.message}`;
    }
    throw new ApiError(errorMessage);
  }
}
