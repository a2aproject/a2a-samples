---
name: frankfurter
description: Fetch currency exchange rates from the frankfurter.dev API
---
# frankfurter

Fetch currency exchange rates from the frankfurter.dev API.

## get_latest_rates
Retrieve the latest exchange rates.

<!-- markdownlint-disable-next-line MD034 -->
- **Base URL**: https://api.frankfurter.dev
- **Method**: GET
- **Endpoint**: /v1/latest
- **Parameters**:
  - base (string): The base currency symbol (default: EUR).
  - symbols (string): A comma-separated list of target currency symbols to filter.

## get_historical_rates
Retrieve exchange rates for a specific past date.

<!-- markdownlint-disable-next-line MD034 -->
- **Base URL**: https://api.frankfurter.dev
- **Method**: GET
- **Endpoint**: /v1/{date}
- **Parameters**:
  - date (string, required): The date in YYYY-MM-DD format.
  - base (string): The base currency symbol.
  - symbols (string): A comma-separated list of target currency symbols.

## get_time_series_rates
Retrieve exchange rates over a specific time period.

<!-- markdownlint-disable-next-line MD034 -->
- **Base URL**: https://api.frankfurter.dev
- **Method**: GET
- **Endpoint**: /v1/{start_date}..{end_date}
- **Parameters**:
  - start_date (string, required): Start date (YYYY-MM-DD).
  - end_date (string): End date (YYYY-MM-DD). If omitted, defaults to the current date.
  - base (string): The base currency symbol.
  - symbols (string): A comma-separated list of target currency symbols.

## get_available_currencies
Retrieve a list of all available currency symbols and their full names.

<!-- markdownlint-disable-next-line MD034 -->
- **Base URL**: https://api.frankfurter.dev
- **Method**: GET
- **Endpoint**: /v1/currencies
