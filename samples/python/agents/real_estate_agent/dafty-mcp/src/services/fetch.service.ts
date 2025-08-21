import axios from 'axios';
import logger from '../logger.js';
import { config } from '../config.js';
import { ScraperError } from '../errors.js';
import { delay } from '../utils/network.utils.js';

/**
 * Fetches the HTML content of a page with retry logic.
 * @param url The URL to fetch.
 * @param pageNumber The page number being fetched (for logging).
 * @returns The HTML content of the page or null if fetching fails.
 */
export async function fetchPageHTML(url: string, pageNumber: number): Promise<string> {
  for (let attempt = 1; attempt <= config.scraping.maxFetchRetries + 1; attempt++) {
    logger.info(`[fetch.service.ts] Fetching HTML for page ${pageNumber} from ${url} (Attempt ${attempt})`);
    try {
      const response = await axios.get(url, {
        headers: {
          'User-Agent': config.scraping.userAgent,
          Accept:
            'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
          'Accept-Encoding': 'gzip, deflate, br, zstd',
          'Accept-Language': 'en-US,en;q=0.9',
          Referer: 'https://www.google.com/',
        },
        timeout: config.scraping.requestTimeout,
      });
      logger.info(`[fetch.service.ts] HTML fetched successfully for page ${pageNumber}. Status: ${response.status}`);
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error) && error.response?.status === 404) {
        logger.warn(`[fetch.service.ts] Page ${pageNumber} not found (404): ${url}. Skipping.`);
        return ''; // Return empty string to signal skipping this URL
      }
      const errorMsg = error instanceof Error ? error.message : 'An unknown error occurred during fetch.';
      logger.error(`[fetch.service.ts] Error fetching page ${pageNumber} (Attempt ${attempt}): ${errorMsg}`);
      if (attempt > config.scraping.maxFetchRetries) {
        throw new ScraperError(`Max retries reached for page ${pageNumber}. Giving up.`);
      }
      await delay(config.scraping.retryDelayMs);
    }
  }
  throw new ScraperError(`Failed to fetch page ${pageNumber} after multiple retries.`);
}
