# Dafty MCP Server

[![License](https://img.shields.io/badge/License-ISC-blue.svg)](https://opensource.org/licenses/ISC)

![Dafty MCP Banner](assets/dafty-mcp.png)

## Disclaimer

**This is an independent, open-source project and is not affiliated with, endorsed, or sponsored by Daft.ie.** This tool is provided for educational and experimental purposes only. The data is scraped from a publicly available website, and its use is subject to the terms of service of that website. The author assumes no liability for the use or misuse of this software. Please use it responsibly and ethically.

This is an MCP (Model Context Protocol) server designed to interact with Daft.ie, primarily for searching rental properties via web scraping.

## ✨ Features

*   **🔍 Search Rental Properties:** Search for rental listings based on various criteria like location, price range, number of bedrooms, and property type. This tool uses web scraping.
*   **📄 Get Rental Property Details:** Attempts to retrieve detailed information about a specific rental property using its unique ID.
    *   **Note:** This tool relies on the official Daft.ie API (v3) which requires an API key. Without a valid key (set via the `DAFT_API_KEY` environment variable), this tool will likely fail. Refer to `src/daftApi.ts` for more details and a link to the Daft.ie API documentation.

## 🛠️ Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/amineremache/real-estate-agent.git
    cd real-estate-agent/dafty-mcp
    ```
2.  **Install dependencies:**
    ```bash
    npm install
    ```
3.  **Build the server:**
    ```bash
    npm run build
    ```
4.  **Testing (Optional but Recommended):**
    The project uses Vitest for unit testing. To run tests:
    ```bash
    npm test
    ```
    To run tests in watch mode:
    ```bash
    npm run test:watch
    ```
5.  **Configure MCP Settings:**
    Add the following configuration to your MCP settings file (e.g., `~/.config/Code/User/globalStorage/rooveterinaryinc.roo-cline/settings/mcp_settings.json`):

    ```json
    {
      "mcpServers": {
        "dafty-mcp": {
          "command": "node",
          "args": ["~/dafty-mcp/build/index.js"],
          "env": {},
          "disabled": false,
          "alwaysAllow": []
        }
      }
    }
    ```

## 🚀 Usage

Once the MCP server is configured and running, you can use the following tools:

*   `use_mcp_tool` with `server_name: "dafty-mcp"` and `tool_name: "search_rental_properties"`
*   `use_mcp_tool` with `server_name: "dafty-mcp"` and `tool_name: "get_rental_property_details"`

**Example: Searching for rental properties in Dublin**

```xml
<use_mcp_tool>
<server_name>dafty-mcp</server_name>
<tool_name>search_rental_properties</tool_name>
<arguments>
{
  "location": "Dublin",
  "min_price": 1000,
  "max_price": 2000,
  "num_beds": 2
}
</arguments>
</use_mcp_tool>
```

**Example: Getting details for a specific property**

```xml
<use_mcp_tool>
<server_name>dafty-mcp</server_name>
<tool_name>get_rental_property_details</tool_name>
<arguments>
{
  "property_id": "1234567"
}
</arguments>
</use_mcp_tool>