import { URLSearchParams } from 'url';
import type { TextContent } from '@modelcontextprotocol/sdk/types.js';
import type { SearchRentalPropertiesParams, Property } from '../types.js';
import { slugify, generateDaftLocationSlug } from '../utils/parser.utils.js';
import { delay } from '../utils/network.utils.js';
import { config } from '../config.js';
import logger from '../logger.js';
import { fetchPageHTML } from './fetch.service.js';
import { parseSearchResults, parsePropertyDetails, getTotalPages } from './parser.service.js';
import { filterProperties } from './filter.service.js';
import { ScraperError } from '../errors.js';

export async function handleSearchRentalPropertiesScraping(
  params: SearchRentalPropertiesParams
): Promise<{ content: TextContent[]; isError?: boolean }> {
  logger.info('--- daftScraper.service.ts: handleSearchRentalPropertiesScraping CALLED ---');
  logger.info('[daftScraper.service.ts] Received parameters:', params);

  try {
    const baseUrl = buildSearchUrl(params);
    const allProperties = await scrapeAllPages(baseUrl);
    const filteredProperties = filterProperties(allProperties, params);

    logger.info(
      `[daftScraper.service.ts] Found ${allProperties.length} raw scraped items, ${filteredProperties.length} after applying user filters.`
    );

    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify(filteredProperties, null, 2),
        },
      ],
    };
  } catch (error) {
    const message = error instanceof Error ? error.message : 'An unknown error occurred during scraping.';
    throw new ScraperError(`Failed to scrape properties with params: ${JSON.stringify(params)}. Error: ${message}`);
  }
}

function buildSearchUrl(params: SearchRentalPropertiesParams): string {
  let urlPath = `/property-for-rent/ireland`;
  const queryParams = new URLSearchParams();
  const { location, minPrice, maxPrice, numBeds, propertyType } = params;

  const locations = Array.isArray(location) ? location : location ? [location] : [];

  if (locations.length === 1) {
    const locationSlug = generateDaftLocationSlug(locations[0]);
    if (locationSlug) {
      urlPath = `/property-for-rent/${locationSlug}`;
    }
  } else if (locations.length > 1) {
    locations.forEach((loc) => {
      if (loc && loc.trim() !== '') {
        const locationSlug = generateDaftLocationSlug(loc);
        if (locationSlug) {
          queryParams.append('location', locationSlug);
        }
      }
    });
  }

  if (propertyType) {
    const propertyTypeSlug = slugify(propertyType);
    if (propertyTypeSlug === 'apartment') {
      urlPath += '/apartments';
    } else if (propertyTypeSlug === 'house') {
      urlPath += '/houses';
    } else {
      urlPath += `/${propertyTypeSlug}s`;
    }
  }

  if (minPrice) queryParams.append('rentalPrice_from', minPrice.toString());
  if (maxPrice) queryParams.append('rentalPrice_to', maxPrice.toString());
  if (numBeds !== undefined) {
    queryParams.append('numBeds_from', numBeds.toString());
    queryParams.append('numBeds_to', numBeds.toString());
  }

  const url = new URL(urlPath, config.daft.baseUrl);
  url.search = queryParams.toString();
  logger.info(`[daftScraper.service.ts] Constructed base search URL: ${url.href}`);
  return url.href;
}

async function scrapeAllPages(baseUrl: string): Promise<Property[]> {
  let currentPage = 1;
  let totalPages = 1;
  const allProperties: Property[] = [];

  do {
    if (currentPage > 1) {
      await delay(config.scraping.pageDelayMs);
    }

    const pageUrl = currentPage === 1 ? baseUrl : `${baseUrl}${baseUrl.includes('?') ? '&' : '?'}page=${currentPage}`;
    const html = await fetchPageHTML(pageUrl, currentPage);

    if (currentPage === 1) {
      totalPages = getTotalPages(html);
    }

    const propertiesOnPage = parseSearchResults(html);
    const detailedProperties: Property[] = [];
    for (const p of propertiesOnPage) {
      if (!p.url) continue;
      await delay(config.scraping.detailDelayMs); // Delay between detail page fetches
      const detailHtml = await fetchPageHTML(p.url, 0); // 0 indicates a detail page
      const enhancedProperty = parsePropertyDetails(detailHtml, p);
      if (enhancedProperty.units && enhancedProperty.units.length > 0) {
        detailedProperties.push(...(enhancedProperty.units as Property[]));
      } else {
        detailedProperties.push(enhancedProperty as Property);
      }
    }

    allProperties.push(...detailedProperties);
    currentPage++;
  } while (currentPage <= totalPages);

  return allProperties;
}
