# Contributing to Agent2Agent (A2A) Samples

We'd love to accept your patches and contributions to this project. This repository contains code samples and demos demonstrating the [Agent2Agent (A2A) Protocol](https://goo.gle/a2a).

## Table of Contents

- [Before You Begin](#before-you-begin)
- [Contribution Process](#contribution-process)
- [Development Workflow](#development-workflow)

## Before You Begin

### Prerequisites (for Python agents)

Ensure your local environment meets the following requirements before starting development:

- **Python**: Version 3.12 or higher (3.13+ recommended for agent development).
- **Package Manager**: [uv](https://docs.astral.sh/uv/) is required for managing dependencies and workspaces.

### Local Setup

1. **Fork and Clone**: [Fork this repository](https://github.com/a2aproject/a2a-samples/fork) to your GitHub account, then clone your fork locally:
   ```bash
   git clone https://github.com/<your-username>/a2a-samples.git
   cd a2a-samples
   ```

2. **Install Dependencies**: Ensure your workspace dependencies are installed:
   ```bash
   uv sync
   ```

3. **Create a Branch**: Create a feature branch for your changes:
   ```bash
   git checkout -b feature/my-new-sample
   ```

## Contribution Process

### Issues and Proposals

Before undertaking significant work, check the [issues page](https://github.com/a2aproject/a2a-samples/issues) to see if your feature or bug fix is already being discussed. If not, open a new issue to discuss your proposed changes.

### Code Reviews

All submissions, including submissions by project members, require review using GitHub pull requests. Consult [GitHub Help](https://help.github.com/articles/about-pull-requests/) for more information on using pull requests.

## Development Workflow

We use `uv` for dependency management, linting, formatting, type checking, and testing. Make sure all checks pass before submitting a pull request.

### Formatting and Linting

All code **must** be formatted and linted using `ruff` tool. Check its [.ruff.toml](.ruff.toml) configration for more details.

To check and automatically fix linting errors across the workspace:

```bash
uv run ruff check --fix
```

To format the codebase:

```bash
uv run ruff format
```

#### Checking a Specific Sample

If you are working on a single agent sample (e.g., `helloworld`), you can target it directly:

```bash
uv run ruff check --fix --config .ruff.toml samples/python/agents/helloworld/
uv run ruff format --config .ruff.toml samples/python/agents/helloworld/
```

Alternatively, you can use [./format.sh](./format.sh) for formatting Python and Notebook files.

### Type Checking

Use static type checks to improve your code readability and maintainability. Run the following commands from the workspace root or target directory:

```bash
uv run mypy samples/python
uv run pyright samples/python
```

### Testing and Coverage

Run the tests using `pytest`. Use `--verbose` for more detailed output.

```bash
uv run pytest --verbose
```

#### Testing a Specific Sample

To run tests for a specific agent sample or extension:

```bash
uv run pytest tests/python/agents/<sample-name>/
```

#### Checking Test Coverage

When adding new source code or features, verify test coverage before committing:

```bash
uv run pytest --cov=samples/python --cov-report=term-missing
```
