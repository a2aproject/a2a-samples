import express, { Request, Response } from 'express';
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { SSEServerTransport } from '@modelcontextprotocol/sdk/server/sse.js';
import type { TextContent } from '@modelcontextprotocol/sdk/types.js';
import {
  SearchRentalPropertiesInputSchema,
  GetRentalPropertyDetailsInputSchema,
  ParseQueryInputSchema,
} from './types.js';
import { handleSearchRentalPropertiesScraping } from './services/daftScraper.service.js';
import { handleGetRentalPropertyDetailsApi } from './services/daftApi.service.js';
import { parseQueryWithLLM } from './services/queryParser.service.js';
import logger from './logger.js';
import { createErrorResponse } from './utils/error.utils.js';
import { ValidationError } from './errors.js';

export async function startServer() {
  const server = new McpServer({
    name: 'dafty-mcp',
    version: '0.2.4',
  });

  // Tool for searching rental properties (uses scraper)
  server.tool(
    'search_rental_properties',
    SearchRentalPropertiesInputSchema.shape as Record<string, unknown>, // Use .shape for MCP SDK
    async (extra: Record<string, unknown>): Promise<{ content: TextContent[]; isError?: boolean }> => {
      try {
        const parseResult = SearchRentalPropertiesInputSchema.safeParse(extra);
        if (!parseResult.success) {
          throw new ValidationError('Invalid parameters received.', parseResult.error.flatten().fieldErrors);
        }
        return await handleSearchRentalPropertiesScraping(parseResult.data);
      } catch (error) {
        return createErrorResponse(error, 'search_rental_properties', extra);
      }
    }
  );

  // Tool for getting rental property details (uses API - likely non-functional)
  server.tool(
    'get_rental_property_details',
    GetRentalPropertyDetailsInputSchema.shape as Record<string, unknown>, // Use .shape for MCP SDK
    async (extra: Record<string, unknown>): Promise<{ content: TextContent[]; isError?: boolean }> => {
      try {
        const parseResult = GetRentalPropertyDetailsInputSchema.safeParse(extra);
        if (!parseResult.success) {
          throw new ValidationError('Invalid parameters received.', parseResult.error.flatten().fieldErrors);
        }
        logger.info(
          '[server.ts] get_rental_property_details tool called. Note: This uses the Daft.ie API which likely requires an unobtainable API key and may not function.'
        );
        return await handleGetRentalPropertyDetailsApi(parseResult.data);
      } catch (error) {
        return createErrorResponse(error, 'get_rental_property_details', extra);
      }
    }
  );

  const app = express();
  const port = Number(process.env.PORT) || 4000;

  class SseManager {
    private clients: Map<string, SSEServerTransport> = new Map();

    add(req: Request, res: Response) {
      const transport = new SSEServerTransport('/message', res);
      const clientId = transport.sessionId;
      this.clients.set(clientId, transport);
      server.connect(transport);

      req.on('close', () => {
        this.remove(clientId);
      });
    }

    remove(clientId: string) {
      this.clients.delete(clientId);
      logger.info(`Client ${clientId} disconnected.`);
    }

    handlePost(req: Request, res: Response) {
      let clientId = req.headers['x-mcp-client-id'] as string | undefined;

      // Workaround for Python client sending sessionId in query instead of header
      if (!clientId && req.query.sessionId && typeof req.query.sessionId === 'string') {
        logger.info(`[server.ts] Falling back to sessionId from query parameter for client ID.`);
        clientId = req.query.sessionId;
      }

      if (!clientId) {
        res.status(400).send('Missing or invalid X-MCP-Client-ID header or sessionId query parameter');
        return;
      }

      const transport = this.clients.get(clientId);
      if (transport) {
        transport.handlePostMessage(req, res, req.body);
      } else {
        res.status(404).send(`No active SSE transport for client ID: ${clientId}`);
      }
    }
  }

  const sseManager = new SseManager();

  app.get('/sse', (req: Request, res: Response) => {
    sseManager.add(req, res);
  });

  app.post('/message', express.json(), (req: Request, res: Response) => {
    sseManager.handlePost(req, res);
  });

  app.get('/health', (_req: Request, res: Response) => {
    res.status(200).send('OK');
  });

  // Tool for parsing a natural language query
  server.tool(
    'parse_query',
    ParseQueryInputSchema.shape as Record<string, unknown>,
    async (extra: Record<string, unknown>): Promise<{ content: TextContent[]; isError?: boolean }> => {
      try {
        const parseResult = ParseQueryInputSchema.safeParse(extra);
        if (!parseResult.success) {
          throw new ValidationError('Invalid parameters received.', parseResult.error.flatten().fieldErrors);
        }
        const parsedParams = await parseQueryWithLLM(parseResult.data.query);
        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify(parsedParams, null, 2),
            },
          ],
        };
      } catch (error) {
        return createErrorResponse(error, 'parse_query', extra);
      }
    }
  );

  app.listen(port, () => {
    logger.info(
      `Dafty MCP server (refactored) running on http://localhost:${port}. Search uses scraping. Details uses API (likely non-functional).`
    );
  });
}
