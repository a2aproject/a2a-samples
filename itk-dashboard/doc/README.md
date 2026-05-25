# A2A ITK Compatibility Dashboard: Technical Guide

This document describes how to interpret the A2A Integration Test Kit (ITK) Compatibility Dashboard and outlines how the underlying test metrics are produced and synchronized.

---

## 🔍 How to Read the Dashboard

The dashboard consists of a history sidebar on the left and a main panel containing topology cards on the right.

### 1. History Timeline Sidebar (Left Panel)
* The left sidebar displays the history of recent nightly runs.
* Selecting a run in the list loads and displays the test outcomes for that specific run.
* **Commit Links**: The **Commit SHA** in the header links directly to the GitHub commit that triggered the run.

### 2. Topology Cards (Main Panel)
* The main panel displays a card for each distinct SDK network topology configuration.
* Each card contains a graphical representation of the network nodes on the left and a consolidated **Compatibility Matrix** on the right.

### 3. Core Integration Test Execution Model
Each topology card represents a set of integration test scenarios executed across the network graph. These tests function as follows:
* **Bi-Directional Traversal**: The framework generates an Eulerian Circuit (a closed path that visits every directed edge exactly once) to execute a complete, bi-directional traversal across all SDK nodes in the topology.
* **Asymmetric Roles Validation**:
  * **Active Client Role**: Verifies that the `current` SDK version (the development version currently under test) successfully initiates and executes requests/actions acting as a client in relation to all stable, historical SDK nodes in the topology.
  * **Active Server/Receiver Role**: Verifies that the `current` SDK version successfully receives, processes, and responds to requests, events, or subscriptions initiated by those stable, historical SDK nodes acting as clients.

### 4. Node Versioning
Inside the node rectangles in the topology graph:
* **`current`**: Corresponds to the latest development version built from the `main` branch of the SDK repository.
* **Tagged Versions (e.g., `python_v10`, `go_v03`)**: Corresponds to released historical versions of the SDKs.

### 5. Compatibility Matrix
The matrix maps communication protocols to testing behaviors:
* **Protocols**: `jsonrpc`, `grpc`, `http_json`.
* **Behaviors**:
  * `Send Message` (Non-streaming message exchange)
  * `Send Message (Streaming)` (Asynchronous stream-based exchange)
  * `Push Notification` (Push-notification delivery verification)
  * `Resubscribe` (Client-side subscription state recovery)

### 6. Maximal Graph Selection
For each protocol and behavior, the tests are run on the largest compatible topology (maximal graph) that supports that specific combination.
* **Status Indicators**:
  * **Green (`PASS`)**: All integration tests for the protocol and behavior combination on this topology succeeded.
  * **Red (`FAIL`)**: One or more integration tests failed.
  * **Gray (`-`)**: The protocol or behavior is not supported by the SDK versions in the topology (e.g., `go_v03` does not support `http_json`).

---

## ⚙️ Data Pipeline Architecture

The dashboard is hosted as a static website and updated via a daily scheduled workflow.

### Step 1: SDK Nightly Test Runs
Each SDK repository runs a scheduled workflow every night:
1. Runs the compatibility test suite against defined scenarios.
2. Appends the results to a rolling history JSON file (e.g., `itk_python.json`), keeping the last 50 runs.
3. Uploads the JSON file as a release asset under the `nightly-metrics` release tag in that SDK's repository.

### Step 2: Dashboard Deployment Sync Job
The central `a2a-samples` repository runs a daily deployment workflow:
1. Downloads the latest `itk_python.json` (and other SDK JSON files once available) from the public GitHub release assets.
2. Places the downloaded JSON files in the `/itk-dashboard` directory.
3. Publishes the directory to GitHub Pages:
   👉 `https://a2aproject.github.io/a2a-samples/itk-dashboard/`

---

## 🛠️ Contribution Guide & Code Locations

The Integration Test Kit (ITK) framework and the dashboard are structured across the following directories inside the `a2a-samples` repository:

* **Integration Test Kit (ITK)**: [Core Test Kit](https://github.com/a2aproject/a2a-samples/tree/implement-itk-service/itk/)
  * Contains the central test runner, HTTP mock notification server, SDK agents configurations, and test suites.
* **Dashboard Code**: [Dashboard Code](https://github.com/a2aproject/a2a-samples/tree/main/itk-dashboard/)
  * Static index page, stylesheets, and rendering scripts.

### How to Contribute
* **Dashboard Contributions**:
  * All enhancements or corrections to the **Interoperability Dashboard** (`/itk-dashboard`) must target the **`main`** branch. To contribute:
    1. Create a local feature branch originating from the `main` branch.
    2. Implement your modifications and open a Pull Request targeting the **`main`** branch.
* **ITK Core & Scenario Contributions**:
  * All active development on the **ITK Framework & Test Suites** (`/itk`) resides on the **`implement-itk-service`** branch. To contribute:
    1. Create a local feature branch originating from the `implement-itk-service` branch.
    2. Add/modify scenario definitions or launchers, and open a Pull Request targeting the **`implement-itk-service`** branch.

---

## 📋 Future Development Roadmap (Backlog)

We are actively tracking the following development initiatives to expand coverage and increase observability:

### 1. Integration Test Kit (ITK) Backlog
* **Error & Specification-Deviation Testing**:
  * Verify that the test suite correctly simulates, catches, and validates specified protocol errors when an agent behaves incorrectly or in a way that contradicts the A2A specification.
* **Multi-SDK Support Expansion**:
  * Implement and mature standard nightly test suites for the remaining SDK configurations: **TypeScript**, **Rust**, **.NET**, and **Java**.

### 2. Compatibility Dashboard Backlog
* **Aggregated SDK-Comparison Matrix**:
  * Design a side-by-side matrix view/tab comparing multiple SDKs across their A2A protocol compliance scores.
* **Historical Run Trends**:
  * Support comparison of results across historical nightly runs to track stability trends over time.
* **Visual Log Explorer**:
  * Implement an interactive in-browser utility to view, search, and analyze local log files generated by each SDK node during a test run.
