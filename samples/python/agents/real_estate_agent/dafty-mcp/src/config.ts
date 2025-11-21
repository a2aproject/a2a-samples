export const config = {
  daft: {
    baseUrl: process.env.DAFT_BASE_URL || 'https://www.daft.ie',
    apiBaseUrl: process.env.DAFT_API_BASE_URL || 'https://api.daft.ie/v3',
    apiKey: process.env.DAFT_API_KEY,
  },
  scraping: {
    maxPagesToFetch: 1,
    maxFetchRetries: 2,
    retryDelayMs: 2000,
    requestTimeout: 10000,
    pageDelayMs: 1500,
    detailDelayMs: 500,
    userAgent:
      'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
  },
  logging: {
    logLevel: process.env.LOG_LEVEL || 'info',
  },
  ollama: {
    baseUrl: process.env.OLLAMA_BASE_URL || 'http://ollama:11434',
  }
};
