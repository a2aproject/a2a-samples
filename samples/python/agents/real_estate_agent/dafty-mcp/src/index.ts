#!/usr/bin/env node
import { startServer } from './server.js';
import logger from './logger.js';

startServer().catch((error) => {
  logger.error('Failed to start Daft.ie MCP server:', error);
  process.exit(1);
});
