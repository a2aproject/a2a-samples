import { Ollama } from 'llamaindex';
import { SearchRentalPropertiesParams } from '../types.js';
import logger from '../logger.js';
import { LlmError } from '../errors.js';
import { config } from '../config.js';

// Initialize the LLM
const ollama = new Ollama({
  model: 'tinydolphin',
  temperature: 0.1,
  baseURL: config.ollama.baseUrl,
});

async function callLLM(query: string): Promise<Partial<SearchRentalPropertiesParams>> {
  logger.info(`[queryParser.service.ts] Calling LLM to parse query: "${query}"`);

  const prompt = `
    You are an expert at extracting structured information from user queries.
    Given the following query, extract the location, maximum price, and number of bedrooms.
    Return the result as a valid JSON object with the keys "location", "maxPrice", and "numBeds".
    If a value is not present in the query, do not include the corresponding key in the JSON object.
    The output must only be the JSON object, with no other text or explanations.

    Query: "${query}"

    JSON:
  `;

  const response = await ollama.chat({
    messages: [{ content: prompt, role: 'user' }],
  });

  const content = response.message.content;
  logger.info(`[queryParser.service.ts] Raw LLM response: ${content}`);

  // Find the start and end of the JSON object to robustly extract it,
  // even if the LLM includes extra text or markdown.
  const startIndex = content.indexOf('{');
  const endIndex = content.lastIndexOf('}');

  if (startIndex === -1 || endIndex === -1 || endIndex < startIndex) {
    throw new Error('LLM did not return a valid JSON object.');
  }

  const jsonString = content.substring(startIndex, endIndex + 1);
  const result = JSON.parse(jsonString);
  const sanitizedResult = sanitizeLLMOutput(result);

  logger.info(`[queryParser.service.ts] LLM parsed filters:`, sanitizedResult);
  return sanitizedResult;
}

interface RawLLMOutput {
  location?: string;
  maxPrice?: string | number;
  numBeds?: string | number;
  propertyType?: string;
}

function sanitizeLLMOutput(data: RawLLMOutput): Partial<SearchRentalPropertiesParams> {
  const sanitized: Partial<SearchRentalPropertiesParams> = {};

  if (data.location && typeof data.location === 'string') {
    sanitized.location = data.location;
  }

  if (data.maxPrice) {
    const priceString = String(data.maxPrice).replace(/[€,]/g, '');
    const price = parseInt(priceString, 10);
    if (!isNaN(price)) {
      sanitized.maxPrice = price;
    }
  }

  if (data.numBeds) {
    const beds = parseInt(String(data.numBeds), 10);
    if (!isNaN(beds)) {
      sanitized.numBeds = beds;
    }
  }

  if (data.propertyType && typeof data.propertyType === 'string') {
    sanitized.propertyType = data.propertyType;
  }

  return sanitized;
}

export async function parseQueryWithLLM(query: string): Promise<Partial<SearchRentalPropertiesParams>> {
  try {
    const parsedParams = await callLLM(query);
    return parsedParams;
  } catch (error) {
    logger.error('[queryParser.service.ts] Error parsing query with LLM:', error);
    const message = error instanceof Error ? error.message : 'An unknown error occurred during query parsing.';
    throw new LlmError(message);
  }
}
