# HOW TO RUN the Secure Passport Extension Sample

This guide provides step-by-step instructions for setting up the environment and running the Python sample code for the **Secure Passport Extension v1**.

The sample is located in the `samples/python/` directory.

---

## 1. Prerequisites

You need the following installed on your system:

* **Python** (version 3.9 or higher)
* **Poetry** (Recommended for dependency management via `pyproject.toml`)

---

## 2. Setup and Installation

1. **From the repository root, navigate** to the sample project directory:
    ```bash
    cd extensions/secure-passport/v1/samples/python
    ```

2. **Install Dependencies** using Poetry. This command reads `pyproject.toml`, creates a virtual environment, and installs `pydantic` and `pytest`.
    ```bash
    poetry install
    ```

3. **Activate** the virtual environment:
    ```bash
    poetry shell
    ```

    *(Note: All subsequent commands are run from within this activated environment.)*

---

## 3. Execution

There are two ways to run the code: using the automated unit tests or using a manual script.

### A. Run Unit Tests (Recommended)

Running the tests is the most complete way to verify the extension's data modeling, integrity checks, and validation logic.

```bash
# Execute Pytest against the test directory
pytest tests/

### B. Run Middleware Demo Script

Execute `run.py` to see the full client/server middleware pipeline in action for all four use cases:

```bash
python run.py

### Expected Console Output

The output below demonstrates the successful execution of the four use cases via the simulated middleware pipeline:

========================================================= Secure Passport Extension Demo (Middleware)
--- Use Case: Efficient Currency Conversion (via Middleware) ---
[PIPELINE] Client Side: Middleware -> Transport
[Middleware: Client] Attaching Secure Passport for a2a://travel-orchestrator.com
[Transport] Message sent over the wire.
[PIPELINE] Server Side: Middleware -> Agent Core
[Middleware: Server] Extracted Secure Passport. Verified: True
[Agent Core] Task received for processing.
[Agent Core] Executing task with verified context: Currency=GBP, Tier=Silver

--- Use Case: Personalized Travel Booking (via Middleware) ---
[PIPELINE] Client Side: Middleware -> Transport
[Middleware: Client] Attaching Secure Passport for a2a://travel-portal.com
[Transport] Message sent over the wire.
[PIPELINE] Server Side: Middleware -> Agent Core
[Middleware: Server] Extracted Secure Passport. Verified: True
[Agent Core] Task received for processing.
[Agent Core] Executing task with verified context: Currency=Unknown, Tier=Platinum

--- Use Case: Proactive Retail Assistance (via Middleware) ---
[PIPELINE] Client Side: Middleware -> Transport
[Middleware: Client] Attaching Secure Passport for a2a://ecommerce-front.com
[Transport] Message sent over the wire.
[PIPELINE] Server Side: Middleware -> Agent Core
[Middleware: Server] Extracted Secure Passport. Verified: False
[Agent Core] Task received for processing.
[Agent Core] Executing task with unverified context (proceeding cautiously).

--- Use Case: Marketing Agent seek insights (via Middleware) ---
[PIPELINE] Client Side: Middleware -> Transport
[Middleware: Client] Attaching Secure Passport for a2a://marketing-agent.com
[Transport] Message sent over the wire.
[PIPELINE] Server Side: Middleware -> Agent Core
[Middleware: Server] Extracted Secure Passport. Verified: True
[Agent Core] Task received for processing.
[Agent Core] Executing task with verified context: Currency=Unknown, Tier=Standard
