# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.3] - 2025-06-18

### Added
- **Developer Tooling:**
    - Added ESLint and Prettier for code linting and formatting.
    - Added Winston for structured logging.
- **Configuration:**
    - Centralized all configuration into a new `src/config.ts` file.

### Changed
- **Project Structure:**
    - Refactored source code into a more modular structure with `services`, `utils`, `config`, and `types` directories.
- **Scraping Enhancements:**
    - The `search_rental_properties` tool now accepts an array of locations.
    - Improved parsing logic for property details.

## [0.2.2] - 2025-06-17

### Added
- **Scraper Enhancements:**
    - Implemented a two-pass scraping system to visit each property's detail page, enabling the extraction of more accurate data like coordinates and BER ratings.
    - Added support for parsing multi-unit developments.

### Fixed
- **Build Script:**
    - Corrected the build script in `package.json` to handle the new project structure.

## [0.2.1] - 2025-06-14

### Added
- **Unit Testing:**
    - Integrated Vitest for unit testing.
    - Added test scripts (`test`, `test:watch`) to `package.json`.
    - Created comprehensive unit tests for `parsePrice`, `parseBeds`, and `slugify` helper functions in `daftScraper.ts`.
- **Logging & Error Handling:**
    - MCP tools now return structured JSON error messages for input validation failures (`src/index.ts`) and scraping errors (`src/daftScraper.ts`), providing more context.
    - Enhanced server-side `console.error` logs to include these structured error details.
    - Added detailed `console.warn` logging in `daftScraper.ts` when primary CSS selectors fail and fallbacks are used.
    - Implemented more specific logging for pagination termination conditions in `daftScraper.ts`.
- **API Disclaimer:**
    - Added a prominent disclaimer at the top of `src/daftApi.ts` regarding the API key requirement for the `get_rental_property_details` tool.

### Changed
- **Scraper Enhancements (`daftScraper.ts`):**
    - `parsePrice` function now returns a structured object `{ value: number | null, type: "numeric" | "on_application" | "unknown" }` to explicitly handle different price types. Code using `parsedPrice` updated accordingly.
    - Refined client-side location filtering: for "Ringsend" searches, it now includes checks for synonymous/nearby terms like "Irishtown", "Grand Canal Dock", "Dublin 4", and "Dublin 2".
    - Implemented a retry mechanism with delays in the `fetchPageHTML` function for increased robustness.
- `.gitignore`: Added `package-lock.json`.

### Fixed
- Corrected `slugify` function in `daftScraper.ts` to properly handle leading/trailing spaces by adding `.trim()`.
- Ensured helper functions (`parsePrice`, `parseBeds`, `slugify`) in `daftScraper.ts` are correctly exported for testing.
- Configured Vitest (`vitest.config.ts`) to only run tests from the `src` directory, resolving issues with tests in the `build` directory.


## [0.2.0] - 2025-06-12

### Added
- Web scraping functionality for the `search_rental_properties` tool to fetch data directly from Daft.ie.
  - Constructs search URLs based on location, price, number of beds, and property type.
  - Parses HTML using Cheerio to extract property details (ID, address, URL, price, beds, property type, tagline, image).
  - Implements filtering of scraped results based on user-provided criteria.
- Helper functions `parsePrice` and `parseBeds` for converting scraped string values to numbers (now located in `daftScraper.ts`).
- More robust CSS selectors with fallbacks for extracting property data within the scraper.

### Changed
- **BREAKING CHANGE (for `search_rental_properties` tool):** The `search_rental_properties` tool now uses web scraping instead of the Daft.ie API due to API access restrictions (403 errors, likely requiring an unavailable API key).
- Refactored MCP server code into separate modules:
  - `daftScraper.ts`: Contains all web scraping logic for property searches.
  - `daftApi.ts`: Contains the (likely non-functional) Daft.ie API client and `get_rental_property_details` tool logic. Added comments regarding API key requirements.
  - `index.ts`: Main entry point, handles server setup, Zod schema definitions, and tool registration using imported handlers.
- Updated `index.ts` to correctly use Zod schema `.shape` for tool registration with manual parsing in callbacks, which then call the typed handlers from `daftScraper.ts` and `daftApi.ts`.
- Improved URL construction logic for Daft.ie scraper to more accurately target locations (e.g., "Dublin 2") and property types based on observed Daft.ie URL patterns.
- Logging for `search_rental_properties` (scraper) now uses `console.error` for operational messages, removing verbose file-based and per-item debugging logs for cleaner production output.

### Fixed
- Resolved "Invalid parameters" error for tool calls by correctly identifying that parameters are passed directly in the `extra` argument when using `.shape` for schema registration and implementing manual parsing in the `index.ts` tool registration callbacks.
- Addressed various TypeScript errors related to Zod schema usage with MCP SDK and callback signatures during the refactoring process.
- Corrected `__dirname` usage for ES module compatibility when file logging was temporarily enabled during debugging.
- Fixed build errors in test files (`tools.spec.ts`) by updating calls to `handleGetRentalPropertyDetails` to match its refactored signature (using `as any` for intentionally invalid test inputs).
- Resolved ESLint parsing errors related to `tsconfig.json` inclusion by adjusting `parserOptions.project` in `.eslintrc.cjs` to be an array.