# HOW TO RUN the Secure Passport Extension Sample

This guide provides step-by-step instructions for setting up the environment and running the Python sample code for the **Secure Passport Extension v1**.

The sample is located in the `samples/python/` directory.

## 1. Prerequisites

You need the following installed on your system:

* **Python** (version 3.9 or higher)
* **Poetry** (Recommended for dependency management via `pyproject.toml`)

## 2. Setup and Installation

1.  **Navigate** to the sample project directory:
    ```bash
    cd extensions/secure-passport/v1/samples/python
    ```

2.  **Install Dependencies** using Poetry. This command reads `pyproject.toml`, creates a virtual environment, and installs `pydantic` and `pytest`.
    ```bash
    poetry install
    ```

3.  **Activate** the virtual environment:
    ```bash
    poetry shell
    ```

    *(Note: All subsequent commands are run from within this activated environment.)*

## 3. Execution

There are two ways to run the code: using the automated unit tests or using a manual script.

### A. Run Unit Tests (Recommended)

Running the tests is the most complete way to verify the extension's data modeling, integrity checks, and validation logic.

```bash
# Execute Pytest against the test directory
pytest tests/
```


=========================================================
         Secure Passport Extension Demo Runner
=========================================================

--- Use Case: Efficient Currency Conversion ---
  Source Agent: a2a://travel-orchestrator.com
  Is Verified: True
  Action: Specialist skips asking for currency and calculates in GBP.

--- Use Case: Personalized Travel Booking ---
  Source Agent: a2a://travel-portal.com
  Is Verified: True
  Action: Specialist filters hotels for Bali, Indonesia and applies Platinum perks.

--- Use Case: Proactive Retail Assistance ---
  Source Agent: a2a://ecommerce-front.com
  Is Verified: False
  Action: Specialist proactively provides reviews for SKU Nikon-Z-50mm-f1.8 based on intent 'seeking_reviews'.

--- Use Case: Marketing Agent seek insights ---
  Source Agent: a2a://marketing-agent.com
  Is Verified: True
  Action: Secured DB Agent confirms scope 'read:finance_db' and runs quarterly_revenue query.