/**
 * Base class for all application-specific errors.
 */
export class AppError extends Error {
  public readonly type: string;

  constructor(message: string, type: string) {
    super(message);
    this.type = type;
    this.name = this.constructor.name;
    Error.captureStackTrace(this, this.constructor);
  }
}

/**
 * Error for issues related to the Daft.ie API.
 */
export class ApiError extends AppError {
  constructor(message = 'An API error occurred.') {
    super(message, 'ApiError');
  }
}

/**
 * Error for issues related to web scraping.
 */
export class ScraperError extends AppError {
  constructor(message = 'A scraping error occurred.') {
    super(message, 'ScraperError');
  }
}

/**
 * Error for input validation failures.
 */
export class ValidationError extends AppError {
  public readonly details: Record<string, unknown>;

  constructor(message = 'A validation error occurred.', details: Record<string, unknown> = {}) {
    super(message, 'ValidationError');
    this.details = details;
  }
}

/**
 * Error for authentication or authorization issues.
 */
export class AuthError extends AppError {
  constructor(message = 'An authentication error occurred.') {
    super(message, 'AuthError');
  }
}

/**
 * Error for issues related to the LLM.
 */
export class LlmError extends AppError {
  constructor(message = 'An LLM error occurred.') {
    super(message, 'LlmError');
  }
}
