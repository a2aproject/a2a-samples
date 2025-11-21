import type { TextContent } from '@modelcontextprotocol/sdk/types.js';
import { AppError, ValidationError } from '../errors.js';
import logger from '../logger.js';

interface ErrorPayload {
  errorType: string;
  toolName?: string;
  message: string;
  details?: Record<string, unknown>;
  receivedParams?: Record<string, unknown>;
}

/**
 * Creates a standardized error response for MCP tools.
 * @param error The error object.
 * @param toolName The name of the tool where the error occurred.
 * @param receivedParams The parameters received by the tool.
 * @returns A content object for the MCP tool response.
 */
export function createErrorResponse(
  error: unknown,
  toolName?: string,
  receivedParams?: Record<string, unknown>
): { content: TextContent[]; isError: true } {
  let payload: ErrorPayload;

  if (error instanceof ValidationError) {
    payload = {
      errorType: error.type,
      toolName,
      message: error.message,
      details: error.details,
      receivedParams,
    };
  } else if (error instanceof AppError) {
    payload = {
      errorType: error.type,
      toolName,
      message: error.message,
      receivedParams,
    };
  } else if (error instanceof Error) {
    payload = {
      errorType: 'UnhandledError',
      toolName,
      message: `An unexpected error occurred: ${error.message}`,
      receivedParams,
    };
  } else {
    payload = {
      errorType: 'UnknownError',
      toolName,
      message: 'An unknown error occurred.',
      receivedParams,
    };
  }

  logger.error(`[${toolName || 'UnknownTool'}] ${payload.message}`, payload);

  return {
    content: [{ type: 'text', text: JSON.stringify(payload, null, 2) }],
    isError: true,
  };
}