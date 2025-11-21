import { describe, it, expect, vi, beforeEach, Mock } from 'vitest';
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { SSEServerTransport } from '@modelcontextprotocol/sdk/server/sse.js';
import { startServer } from '../server.js';
import * as daftScraperService from '../services/daftScraper.service.js';
import * as daftApiService from '../services/daftApi.service.js';
import * as errorUtils from '../utils/error.utils.js';
import * as queryParserService from '../services/queryParser.service.js';

// Mock the entire SDK and services
vi.mock('@modelcontextprotocol/sdk/server/mcp.js');
vi.mock('@modelcontextprotocol/sdk/server/sse.js');
vi.mock('../services/daftScraper.service.js');
vi.mock('../services/daftApi.service.js');
vi.mock('../utils/error.utils.js');
vi.mock('../services/queryParser.service.js');
vi.mock('../logger');

describe('Server Setup', () => {
  let mockServerInstance: McpServer;
  let mockTransportInstance: SSEServerTransport;

  beforeEach(() => {
    vi.resetAllMocks();

    // Mock the McpServer and its methods
    mockServerInstance = {
      tool: vi.fn(),
      connect: vi.fn().mockResolvedValue(undefined),
    } as unknown as McpServer;
    (McpServer as Mock).mockReturnValue(mockServerInstance);

    // Mock the SSEServerTransport
    mockTransportInstance = {} as SSEServerTransport;
    (SSEServerTransport as Mock).mockReturnValue(mockTransportInstance);
  });

  it('should initialize the McpServer', async () => {
    await startServer();
    expect(McpServer).toHaveBeenCalledWith(expect.objectContaining({ name: 'dafty-mcp' }));
  });

  it('should register all tools', async () => {
    await startServer();
    expect(mockServerInstance.tool).toHaveBeenCalledWith(
      'search_rental_properties',
      expect.any(Object),
      expect.any(Function)
    );
    expect(mockServerInstance.tool).toHaveBeenCalledWith(
      'get_rental_property_details',
      expect.any(Object),
      expect.any(Function)
    );
    expect(mockServerInstance.tool).toHaveBeenCalledWith(
      'parse_query',
      expect.any(Object),
      expect.any(Function)
    );
    expect(mockServerInstance.tool).toHaveBeenCalledTimes(3);
  });

  describe('Tool Handlers', () => {
    let toolHandlers: Record<string, (extra: Record<string, unknown>) => Promise<unknown>>;

    beforeEach(async () => {
      toolHandlers = {};
      // Capture the tool handlers by spying on the .tool() method
      (mockServerInstance.tool as Mock).mockImplementation(
        (name: string, _: unknown, handler: (extra: Record<string, unknown>) => Promise<unknown>) => {
          toolHandlers[name] = handler;
        }
      );
      await startServer();
    });

    it('should call handleSearchRentalPropertiesScraping for search_rental_properties', async () => {
      const handlerSpy = vi.spyOn(daftScraperService, 'handleSearchRentalPropertiesScraping');
      await toolHandlers.search_rental_properties({ location: 'Dublin' });
      expect(handlerSpy).toHaveBeenCalledWith({ location: 'Dublin' });
    });

    it('should call handleGetRentalPropertyDetailsApi for get_rental_property_details', async () => {
      const handlerSpy = vi.spyOn(daftApiService, 'handleGetRentalPropertyDetailsApi');
      await toolHandlers.get_rental_property_details({ property_id: '123' });
      expect(handlerSpy).toHaveBeenCalledWith({ property_id: '123' });
    });

    it('should call parseQueryWithLLM for parse_query', async () => {
      const handlerSpy = vi.spyOn(queryParserService, 'parseQueryWithLLM');
      await toolHandlers.parse_query({ query: 'find a house' });
      expect(handlerSpy).toHaveBeenCalledWith('find a house');
    });
  });

  describe('Tool Error Handling', () => {
    let toolHandlers: Record<string, (extra: Record<string, unknown>) => Promise<unknown>>;

    beforeEach(async () => {
      toolHandlers = {};
      (mockServerInstance.tool as Mock).mockImplementation(
        (name: string, _: unknown, handler: (extra: Record<string, unknown>) => Promise<unknown>) => {
          toolHandlers[name] = handler;
        }
      );
      await startServer();
    });

    // Test cases for search_rental_properties
    it('search_rental_properties: should create a validation error for invalid input', async () => {
      const errorSpy = vi.spyOn(errorUtils, 'createErrorResponse');
      await toolHandlers.search_rental_properties({ location: 123 }); // Invalid type
      expect(errorSpy).toHaveBeenCalledWith(expect.any(Error), 'search_rental_properties', { location: 123 });
    });

    it('search_rental_properties: should create an error response on service failure', async () => {
      const error = new Error('Scraper failed');
      vi.spyOn(daftScraperService, 'handleSearchRentalPropertiesScraping').mockRejectedValue(error);
      const errorSpy = vi.spyOn(errorUtils, 'createErrorResponse');
      await toolHandlers.search_rental_properties({ location: 'Dublin' });
      expect(errorSpy).toHaveBeenCalledWith(error, 'search_rental_properties', { location: 'Dublin' });
    });

    // Test cases for get_rental_property_details
    it('get_rental_property_details: should create a validation error for invalid input', async () => {
      const errorSpy = vi.spyOn(errorUtils, 'createErrorResponse');
      await toolHandlers.get_rental_property_details({ property_id: 123 }); // Invalid type
      expect(errorSpy).toHaveBeenCalledWith(expect.any(Error), 'get_rental_property_details', { property_id: 123 });
    });

    it('get_rental_property_details: should create an error response on service failure', async () => {
      const error = new Error('API failed');
      vi.spyOn(daftApiService, 'handleGetRentalPropertyDetailsApi').mockRejectedValue(error);
      const errorSpy = vi.spyOn(errorUtils, 'createErrorResponse');
      await toolHandlers.get_rental_property_details({ property_id: '123' });
      expect(errorSpy).toHaveBeenCalledWith(error, 'get_rental_property_details', { property_id: '123' });
    });

    // Test cases for parse_query
    it('parse_query: should create a validation error for invalid input', async () => {
      const errorSpy = vi.spyOn(errorUtils, 'createErrorResponse');
      await toolHandlers.parse_query({ query: 123 }); // Invalid type
      expect(errorSpy).toHaveBeenCalledWith(expect.any(Error), 'parse_query', { query: 123 });
    });

    it('parse_query: should create an error response on service failure', async () => {
      const error = new Error('LLM failed');
      vi.spyOn(queryParserService, 'parseQueryWithLLM').mockRejectedValue(error);
      const errorSpy = vi.spyOn(errorUtils, 'createErrorResponse');
      await toolHandlers.parse_query({ query: 'a query' });
      expect(errorSpy).toHaveBeenCalledWith(error, 'parse_query', { query: 'a query' });
    });
  });
});