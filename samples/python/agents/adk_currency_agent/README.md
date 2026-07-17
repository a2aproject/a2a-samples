# ADK Currency Agent

A currency conversion agent built using the [Google Agent Development Kit (ADK)](https://github.com/google/adk-python) with support for traceability extension.

Traceability extension helps return tool trajectory data and can help with agent evals in non-prod environments.

## Features

- Currency conversion between multiple supported currencies using Frankfurter.
- A2A (Agent-to-Agent) protocol support.
- Traceability support for returning the tool call trajectory data.

## Prerequisites

- [uv](https://github.com/astral-sh/uv) package manager.
- A valid Google API Key with access to Gemini models.

## Setup

1. **Switch to the agent directory:**
    ```bash
    cd adk_currency_agent
    ```

2. **Set the Google API Key:**
    ```bash
    export ENV=development
    export GOOGLE_API_KEY="your-google-api-key"
    ```

3. **Install dependencies:**
    ```bash
    uv sync
    ```

## Running the Server

You can start the A2A agent server using the following command:

```bash
uv run currency_agent
```

## API Endpoints

- **Agent Card:** `GET http://localhost:10999/.well-known/agent-card.json`
- **A2A Endpoint:** `POST http://localhost:10999/`

### Traceability

The agent supports the Traceability extension. To enable it, include the extension URI in your request:

`X-A2A-Extensions: https://github.com/a2aproject/a2a-samples/extensions/traceability/v1`

Trace information (tool trajectory) will be included in the response metadata under the `github.com/a2aproject/a2a-samples/extensions/traceability/v1/traceability` key.

## Evaluation

The project includes a structured evaluation notebook `agent_eval.ipynb` to assess agent performance using the **Vertex AI Generative AI Evaluation SDK**.

### How to Use

1. **Dependencies**: Ensure the required SDKs are installed (see the first cell in the notebook):
    ```python
    %pip install a2a-sdk google-cloud-aiplatform[evaluation] pandas httpx
    ```
2. **Configuration**: Set your Agent URL and Google Cloud Project ID in the setup cell.
3. **Define Test Data**: Update the `test_sets` dictionary with your evaluation scenarios.
4. **Run Evaluation**: Execute all cells to run the evaluation task and view the results.

### Example Agent Response

```json
Request:

POST http://localhost:10999
Content-Type: application/json
X-A2A-Extensions: https://github.com/a2aproject/a2a-samples/extensions/traceability/v1

{
  "jsonrpc": "2.0",
  "id": 33,
  "method": "message/send",
  "params": {          
    "message": {     
      "role": "user",
      "parts": [
        { "type": "text", "text": "Find the list of supported EU currencies and show the exchange rate with USD in markdown format" }
      ],
      "messageId":"foo4",
      "kind": "message"
    }
  }
}

Response:

{
  "id": 33,
  "jsonrpc": "2.0",
  "result": {
    "artifacts": [
      {
        "artifactId": "05a7e9f4-2fb9-4eb7-906a-997840ce9556",
        "name": "conversion_result",
        "parts": [
          {
            "kind": "text",
            "text": "Here are the supported EU currencies and their exchange rates with USD (as of 2026-03-10):\n\n"
                    "| Currency Code | Currency Name | Exchange Rate (1 USD to) |\n"
                    "| :--- | :--- | :--- |\n"
                    "| **EUR** | Euro | 0.85903 |\n"
                    "| **CZK** | Czech Koruna | 20.943 |\n"
                    "| **DKK** | Danish Krone | 6.4181 |\n"
                    "| **HUF** | Hungarian Forint | 331.44 |\n"
                    "| **PLN** | Polish Złoty | 3.655 |\n"
                    "| **RON** | Romanian Leu | 4.3756 |\n"
                    "| **SEK** | Swedish Krona | 9.1109 |"
          }
        ]
      }
    ],
    "contextId": "1a356b51-8d42-4e5b-b511-9f22772cfd97",
    "history": [
      {
        "contextId": "1a356b51-8d42-4e5b-b511-9f22772cfd97",
        "kind": "message",
        "messageId": "foo4",
        "parts": [
          {
            "kind": "text",
            "text": "Find the list of supported EU currencies and show the exchange rate with USD in markdown format"
          }
        ],
        "role": "user",
        "taskId": "e30a4f7b-dd2d-4973-a5f8-c43a247262ad"
      }
    ],
    "id": "e30a4f7b-dd2d-4973-a5f8-c43a247262ad",
    "kind": "task",
    "metadata": {
      "github.com/a2aproject/a2a-samples/extensions/traceability/v1/traceability": {
        "trace_id": "trace-dd864c98-15d4-456c-b3e0-238c5c10d095",
        "steps": [
          {
            "step_id": "step-635f427d-7d1e-44df-b678-e40483c49c40",
            "trace_id": "trace-dd864c98-15d4-456c-b3e0-238c5c10d095",
            "parent_step_id": null,
            "call_type": "TOOL",
            "name": "get_available_currencies",
            "parameters": {},
            "requests": null,
            "step_type": "tool_call",
            "cost": null,
            "total_tokens": null,
            "additional_attributes": {},
            "latency": 0,
            "start_time": "2026-03-10T21:23:14.974500+00:00",
            "end_time": "2026-03-10T21:23:14.974521+00:00",
            "error": null
          },
          {
            "step_id": "step-342a2a1b-d76e-4fdf-b112-0115258c0fb5",
            "trace_id": "trace-dd864c98-15d4-456c-b3e0-238c5c10d095",
            "parent_step_id": null,
            "call_type": "TOOL",
            "name": "get_available_currencies",
            "parameters": {
              "response": {
                "AUD": "Australian Dollar",
                "BRL": "Brazilian Real",
                "CAD": "Canadian Dollar",
                "CHF": "Swiss Franc",
                "CNY": "Chinese Renminbi Yuan",
                "CZK": "Czech Koruna",
                "DKK": "Danish Krone",
                "EUR": "Euro",
                "GBP": "British Pound",
                "HKD": "Hong Kong Dollar",
                "HUF": "Hungarian Forint",
                "IDR": "Indonesian Rupiah",
                "ILS": "Israeli New Shekel",
                "INR": "Indian Rupee",
                "ISK": "Icelandic Króna",
                "JPY": "Japanese Yen",
                "KRW": "South Korean Won",
                "MXN": "Mexican Peso",
                "MYR": "Malaysian Ringgit",
                "NOK": "Norwegian Krone",
                "NZD": "New Zealand Dollar",
                "PHP": "Philippine Peso",
                "PLN": "Polish Złoty",
                "RON": "Romanian Leu",
                "SEK": "Swedish Krona",
                "SGD": "Singapore Dollar",
                "THB": "Thai Baht",
                "TRY": "Turkish Lira",
                "USD": "United States Dollar"
              }
            },
            "requests": null,
            "step_type": "tool_response",
            "cost": null,
            "total_tokens": null,
            "additional_attributes": {},
            "latency": 0,
            "start_time": "2026-03-10T21:23:15.422659+00:00",
            "end_time": "2026-03-10T21:23:15.422679+00:00",
            "error": null
          },
          {
            "step_id": "step-f6074e92-5c12-4329-9c8e-f1b29e264594",
            "trace_id": "trace-dd864c98-15d4-456c-b3e0-238c5c10d095",
            "parent_step_id": null,
            "call_type": "TOOL",
            "name": "get_latest_rates",
            "parameters": {
              "symbols": "EUR,CZK,DKK,HUF,PLN,RON,SEK",
              "base": "USD"
            },
            "requests": null,
            "step_type": "tool_call",
            "cost": null,
            "total_tokens": null,
            "additional_attributes": {},
            "latency": 0,
            "start_time": "2026-03-10T21:23:17.063173+00:00",
            "end_time": "2026-03-10T21:23:17.063195+00:00",
            "error": null
          },
          {
            "step_id": "step-422817af-930e-4310-bf28-610c588814dc",
            "trace_id": "trace-dd864c98-15d4-456c-b3e0-238c5c10d095",
            "parent_step_id": null,
            "call_type": "TOOL",
            "name": "get_latest_rates",
            "parameters": {
              "response": {
                "amount": 1.0,
                "base": "USD",
                "date": "2026-03-10",
                "rates": {
                  "CZK": 20.943,
                  "DKK": 6.4181,
                  "EUR": 0.85903,
                  "HUF": 331.44,
                  "PLN": 3.655,
                  "RON": 4.3756,
                  "SEK": 9.1109
                }
              }
            },
            "requests": null,
            "step_type": "tool_response",
            "cost": null,
            "total_tokens": null,
            "additional_attributes": {},
            "latency": 0,
            "start_time": "2026-03-10T21:23:17.550544+00:00",
            "end_time": "2026-03-10T21:23:17.550582+00:00",
            "error": null
          }
        ]
      }
    },
    "status": {
      "message": {
        "contextId": "1a356b51-8d42-4e5b-b511-9f22772cfd97",
        "kind": "message",
        "messageId": "afc2973a-a51d-4337-b000-91ea3c950354",
        "parts": [
          {
            "kind": "text",
            "text": "Here are the supported EU currencies and their exchange rates with USD (as of 2026-03-10):\n\n"
                    "| Currency Code | Currency Name | Exchange Rate (1 USD to) |\n"
                    "| :--- | :--- | :--- |\n"
                    "| **EUR** | Euro | 0.85903 |\n"
                    "| **CZK** | Czech Koruna | 20.943 |\n"
                    "| **DKK** | Danish Krone | 6.4181 |\n"
                    "| **HUF** | Hungarian Forint | 331.44 |\n"
                    "| **PLN** | Polish Złoty | 3.655 |\n"
                    "| **RON** | Romanian Leu | 4.3756 |\n"
                    "| **SEK** | Swedish Krona | 9.1109 |"
          }
        ],
        "role": "agent",
        "taskId": "e30a4f7b-dd2d-4973-a5f8-c43a247262ad"
      },
      "state": "completed",
      "timestamp": "2026-03-10T21:23:20.012071+00:00"
    }
  }
}
```
