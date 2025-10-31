import * as cheerio from 'cheerio';
import { config } from '../config.js';
import { parsePrice, parseBeds, slugify, extractLatLng, formatBer } from '../utils/parser.utils.js';
import type { Property, Unit } from '../types.js';
import logger from '../logger.js';

/**
 * Parses the HTML of a search results page to extract property listings.
 * @param html The HTML content of the search results page.
 * @returns An array of property objects.
 */
export function parseSearchResults(html: string): Partial<Property>[] {
  const $ = cheerio.load(html);
  const properties: Partial<Property>[] = [];

  $('ul[data-testid="results"] li[data-testid^="result-"]').each((index, element) => {
    const $element = $(element);
    const property: Partial<Property> = {};

    property.address = $element.find('div[data-tracking="srp_address"] p').first().text().trim();

    let mainLink = $element.find('a[data-testid="card-link"]').first();
    if (mainLink.length === 0) {
      mainLink = $element.find('a.sc-e4e4a161-16.dukjos').first();
    }
    const relativeUrl = mainLink.attr('href');
    if (relativeUrl) {
      property.url = `${config.daft.baseUrl}${relativeUrl}`;
      const urlParts = relativeUrl.split('/');
      property.id = urlParts[urlParts.length - 1];
    }

    if (!property.id) {
      const dataTestId = $element.attr('data-testid');
      if (dataTestId) property.id = dataTestId.replace('result-', '');
    }

    if (!property.url && property.id && property.address) {
      const addressSlug = slugify(property.address);
      property.url = `${config.daft.baseUrl}/for-rent/${addressSlug}/${property.id}`;
    }
    property.tagline = $element.find('div[data-tracking="srp_tagline"] p').first().text().trim();

    let mainPriceString = '';
    const priceSelectors = [
      'p[data-testid="price"]',
      '[class*="TitleBlock__StyledSpan"][class*="price"]',
      'p.csEcJw',
      'div[data-testid="card-price"] p',
    ];
    for (const selector of priceSelectors) {
      const priceElement = $element.find(selector).first();
      if (priceElement.length) {
        mainPriceString = priceElement.text().trim();
        if (mainPriceString) break;
      }
    }
    if (!mainPriceString) {
      const potentialPriceElement = $element.find('p[class^="sc-4c172e97-0"]').first();
      if (potentialPriceElement.length) {
        const potentialPriceText = potentialPriceElement.text().trim();
        if (
          potentialPriceText.includes('€') ||
          /per (month|week)/i.test(potentialPriceText) ||
          /POA|price on application/i.test(potentialPriceText)
        ) {
          mainPriceString = potentialPriceText;
        }
      }
    }
    property.priceString = mainPriceString;
    const parsedPriceResult = parsePrice(mainPriceString);
    property.parsedPrice = parsedPriceResult.value;
    property.priceType = parsedPriceResult.type;

    let mainBedsString = $element.find('[data-testid="beds"]').text().trim();
    const mainBathsString = $element.find('[data-testid="baths"]').text().trim();
    let mainPropertyTypeString = $element.find('[data-testid="property-type"]').text().trim();

    if (!mainBedsString) {
      $element.find('p, span, li').each((i, el) => {
        const text = $(el).text().trim();
        if (text.match(/^\d+\s*Bed/i) || text.toLowerCase().includes('studio')) {
          mainBedsString = text;
          return false;
        }
      });
    }
    property.bedsString = mainBedsString;
    property.parsedBeds = parseBeds(mainBedsString);
    property.bathsString = mainBathsString;

    if (!mainPropertyTypeString) {
      $element.find('p, span, li').each((i, el) => {
        const text = $(el).text().trim();
        const lowerText = text.toLowerCase();
        if (lowerText === 'apartment' || lowerText === 'house' || lowerText === 'studio' || lowerText === 'flat') {
          mainPropertyTypeString = text;
          return false;
        }
      });
    }
    property.propertyTypeString = mainPropertyTypeString;

    let ber = $element.find('div[data-testid="callout-container"] [aria-label^="BER"]').attr('aria-label');
    if (!ber) {
      ber = $element.find('div[data-tracking="srp_ber"]').attr('aria-label');
    }
    if (!ber) {
      ber = $element.find('p[data-testid="ber"]').text().trim();
    }
    if (ber) {
      property.ber = formatBer(ber);
    }

    const latLngElement = $element.find('div.sc-eb305aa9-35.jfAOAq');
    if (latLngElement.length > 0) {
      const latLng = extractLatLng(latLngElement.html() || '', 'a[data-testid="satelite-button"]');
      if (latLng) {
        property.latitude = latLng.lat;
        property.longitude = latLng.lng;
      }
    }

    properties.push(property);
  });

  return properties;
}

/**
 * Parses the HTML of a property details page to extract additional information.
 * @param html The HTML content of the property details page.
 * @param property The property object to enhance.
 * @returns The enhanced property object.
 */
export function parsePropertyDetails(html: string, property: Partial<Property>): Partial<Property> {
  const $ = cheerio.load(html);

  // First, get the definitive lat/lng for this page
  const latLngElement = $('div.sc-eb305aa9-35.jfAOAq');
  if (latLngElement.length > 0) {
    const latLng = extractLatLng(latLngElement.html() || '', 'a[data-testid="satelite-button"]');
    if (latLng) {
      property.latitude = latLng.lat;
      property.longitude = latLng.lng;
    }
  }

  const subUnitElements = $('a[data-testid="sub-unit"]');
  logger.info(`[parser.service.ts] Found ${subUnitElements.length} sub-units for ${property.url}`);
  if (subUnitElements.length > 0) {
    // This is a development page. We will parse its sub-units and return them as individual properties,
    // discarding the parent "development" property which is not a rentable unit itself.
    const subProperties: Property[] = [];
    subUnitElements.each((index, element) => {
      const $unit = $(element);
      const unitDetails: Partial<Property> = {
        // Inherit from parent property
        address: property.address,
        tagline: property.tagline,
        latitude: property.latitude,
        longitude: property.longitude,
      };

      const relativeUrl = $unit.attr('href');
      if (!relativeUrl) return; // Skip if no URL

      unitDetails.url = `${config.daft.baseUrl}${relativeUrl}`;
      const urlParts = relativeUrl.split('/');
      unitDetails.id = urlParts[urlParts.length - 1];

      unitDetails.priceString = $unit.find('p[data-testid="mc-title"]').text().trim();
      const parsedPrice = parsePrice(unitDetails.priceString);
      unitDetails.parsedPrice = parsedPrice.value;
      unitDetails.priceType = parsedPrice.type;

      const detailsContainer = $unit.find('div[class*="eKLMRy"]');
      const spans = detailsContainer.find('span');
      unitDetails.bedsString = spans
        .filter((i, el) => $(el).attr('data-testid') === 'mc-details-first-item')
        .text()
        .trim();
      unitDetails.bathsString = spans
        .filter((i, el) => $(el).attr('data-testid') === 'mc-details-second-item')
        .text()
        .trim();
      unitDetails.propertyTypeString = spans
        .filter((i, el) => $(el).attr('data-testid') === 'mc-details-third-item')
        .text()
        .trim();

      unitDetails.parsedBeds = parseBeds(unitDetails.bedsString);
      if (unitDetails.parsedBeds?.isStudio && !unitDetails.propertyTypeString) {
        unitDetails.propertyTypeString = 'Studio';
      }

      const berElement = $unit.find('div[data-testid="mc-ber"] div');
      if (berElement.length > 0) {
        const berAriaLabel = berElement.attr('aria-label');
        if (berAriaLabel) {
          unitDetails.ber = formatBer(berAriaLabel);
        }
      }

      // Ensure we have a valid property before adding it
      if (unitDetails.id && unitDetails.url && unitDetails.address && unitDetails.priceString) {
        subProperties.push(unitDetails as Property);
      } else {
        const missingData = [];
        if (!unitDetails.id) missingData.push('id');
        if (!unitDetails.url) missingData.push('url');
        if (!unitDetails.address) missingData.push('address');
        if (!unitDetails.priceString) missingData.push('priceString');
        logger.warn(
          `[parser.service.ts] Skipping sub-unit due to missing essential data: [${missingData.join(
            ', '
          )}]. URL: ${unitDetails.url}`
        );
      }
    });

    logger.info(
      `[parser.service.ts] Replaced development page ${property.url} with ${subProperties.length} sub-properties.`
    );
    // This is a bit of a hack, but we're returning the sub-properties in the 'units' field
    // so the main scraper service can flatten them.
    property.units = subProperties;
  } else {
    logger.info(`[parser.service.ts] No sub-units found for ${property.url}. Treating as single property.`);
    // This is a regular page, enhance the original property with any missing details
    if (!property.ber) {
      let detailBer = $('div[data-testid="callout-container"] [aria-label^="BER"]').attr('aria-label');
      if (!detailBer) {
        detailBer = $('p[data-testid="ber"]').text().trim();
      }
      if (!detailBer) {
        detailBer = $('div[data-testid="ber-container"] p').text().trim();
      }
      if (detailBer) {
        property.ber = formatBer(detailBer);
      }
    }
  }
  return property;
}

/**
 * Determines the total number of pages from the search results HTML.
 * @param html The HTML content of the search results page.
 * @returns The total number of pages.
 */
export function getTotalPages(html: string): number {
  const $ = cheerio.load(html);
  const totalResultsString = $('span.sc-4c172e97-0.ioLdWh').first().text();
  logger.info(`[parser.service.ts] Found total results string: "${totalResultsString}"`);
  if (totalResultsString) {
    const match = totalResultsString.match(/of\s*([\d,]+)\s*total results/i);
    if (match && match[1]) {
      const totalResultsRaw = match[1].replace(/,/g, '');
      const totalResults = parseInt(totalResultsRaw, 10);
      if (!isNaN(totalResults)) {
        const calculatedPages = Math.ceil(totalResults / 20); // 20 results per page
        const totalPages = Math.min(calculatedPages, config.scraping.maxPagesToFetch);
        if (calculatedPages > config.scraping.maxPagesToFetch) {
          logger.warn(
            `[parser.service.ts] Calculated total pages (${calculatedPages}) exceeds config.scraping.maxPagesToFetch (${config.scraping.maxPagesToFetch}). Capping at ${totalPages}.`
          );
        }
        logger.info(
          `[parser.service.ts] Extracted total results: ${totalResults}, calculated pages: ${calculatedPages}, effective total pages: ${totalPages}`
        );
        return totalPages;
      }
    }
  }
  return 1;
}
