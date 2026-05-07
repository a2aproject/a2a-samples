# Nightly ITK Compatibility Pipeline: Rolling Release Asset Approach

This document describes the zero-infrastructure, zero-maintenance, and keyless architecture used to run nightly interop tests and store their history across A2A SDK repositories.

---

## Core Architecture: The Rolling Release Asset Pattern

To display nightly test outcomes on a centralized comparative dashboard *without* managing external databases (like GCP Firestore) or abusing Git history (with automated daily commits), we leverage **GitHub Release Assets**.

### Flow Diagram
```mermaid
flowchart TD
    subgraph Go SDK Repo (standalone-itk-go)
        GoNight[Go Nightly Cron] --> GoTest[1. Run ITK Tests]
        GoTest --> GoBuild[2. Compile 'itk_go.json' history]
        GoBuild --> GoCommit[3. Push 'itk_go.json' to rolling Release tag 'nightly-metrics']
    end

    subgraph Python SDK Repo (standalone-itk)
        PyNight[Python Nightly Cron] --> PyTest[1. Run ITK Tests]
        PyTest --> PyBuild[2. Compile 'itk_python.json' history]
        PyBuild --> PyCommit[3. Push 'itk_python.json' to rolling Release tag 'nightly-metrics']
    end

    subgraph Central Dashboard Repo (a2a-samples)
        DB[GitHub Pages Web App]
    end

    User[Developer Browser] --> DB
    DB -- Public HTTPS Fetch --> GoCommit
    DB -- Public HTTPS Fetch --> PyCommit
    
    note right of DB: Renders comparative matrix & timeline chart keylessly!
```

### Why This Approach is Selected

1.  **100% Public & Keyless Read Access:**
    Unlike workflow run artifacts (which require authentication/tokens to fetch via the GitHub REST API), files attached to a public GitHub Release can be downloaded via direct public HTTPS links by any client without keys or tokens:
    *   Go History: `https://github.com/a2aproject/a2a-go/releases/download/nightly-metrics/itk_go.json`
    *   Python History: `https://github.com/a2aproject/a2a-python/releases/download/nightly-metrics/itk_python.json`

2.  **Zero Git History Pollution:**
    Committing history files directly to a Git branch generates hundreds of automated robot commits, bloating the `.git` structure. Uploading a release asset **creates zero git commits**. It simply replaces the file attached to the existing `nightly-metrics` release tag, keeping the codebase history pristine.

3.  **No Cross-Repository Write Access Needed:**
    Each SDK repository's nightly run only writes to its *own* repository releases. The built-in, automatic `GITHUB_TOKEN` has full permissions to do this natively. You don't need to configure SSH Deploy Keys, PATs, or GitHub Apps.

---

## How the Nightly Runner Maintains History

Each nightly run behaves as a state-preserving loop:
1.  **Fetch Existing History:** The runner downloads the currently published `itk_<sdk>.json` file from the public release URL using `curl` or Python's `requests`. If it's the first run (resulting in a 404), it initializes an empty list `[]`.
2.  **Run Tests:** The orchestrator executes the local ITK integration tests.
3.  **Merge & Prune:** The runner compiles the test results into a new JSON record, appends it to the history list, and prunes the list to keep only the **last N entries** (e.g., last 50 runs).
4.  **Upload:** The runner overwrites the rolling Release Asset file in GitHub using the `softprops/action-gh-release` action, keeping the history fresh.
