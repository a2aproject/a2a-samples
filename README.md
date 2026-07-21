# Agent2Agent (A2A) Samples

<a href="https://studio.firebase.google.com/new?template=https%3A%2F%2Fgithub.com%2Fa2aproject%2Fa2a-samples%2Ftree%2Fmain%2F.firebase-studio">
  <picture>
    <source
      media="(prefers-color-scheme: dark)"
      srcset="https://cdn.firebasestudio.dev/btn/try_light_20.svg">
    <source
      media="(prefers-color-scheme: light)"
      srcset="https://cdn.firebasestudio.dev/btn/try_dark_20.svg">
    <img
      height="20"
      alt="Try in Firebase Studio"
      src="https://cdn.firebasestudio.dev/btn/try_blue_20.svg">
  </picture>
</a>

<div style="text-align: right;">
  <details>
    <summary>🌐 Language</summary>
    <div style="text-align: center;">
      <a href="https://openaitx.github.io/view.html?user=a2aproject&project=a2a-samples&lang=en">English</a>
      | <a href="https://openaitx.github.io/view.html?user=a2aproject&project=a2a-samples&lang=zh-CN">简体中文</a>
      | <a href="https://openaitx.github.io/view.html?user=a2aproject&project=a2a-samples&lang=zh-TW">繁體中文</a>
      | <a href="https://openaitx.github.io/view.html?user=a2aproject&project=a2a-samples&lang=ja">日本語</a>
      | <a href="https://openaitx.github.io/view.html?user=a2aproject&project=a2a-samples&lang=ko">한국어</a>
      | <a href="https://openaitx.github.io/view.html?user=a2aproject&project=a2a-samples&lang=hi">हिन्दी</a>
      | <a href="https://openaitx.github.io/view.html?user=a2aproject&project=a2a-samples&lang=th">ไทย</a>
      | <a href="https://openaitx.github.io/view.html?user=a2aproject&project=a2a-samples&lang=fr">Français</a>
      | <a href="https://openaitx.github.io/view.html?user=a2aproject&project=a2a-samples&lang=de">Deutsch</a>
      | <a href="https://openaitx.github.io/view.html?user=a2aproject&project=a2a-samples&lang=es">Español</a>
      | <a href="https://openaitx.github.io/view.html?user=a2aproject&project=a2a-samples&lang=it">Italiano</a>
      | <a href="https://openaitx.github.io/view.html?user=a2aproject&project=a2a-samples&lang=ru">Русский</a>
      | <a href="https://openaitx.github.io/view.html?user=a2aproject&project=a2a-samples&lang=pt">Português</a>
      | <a href="https://openaitx.github.io/view.html?user=a2aproject&project=a2a-samples&lang=nl">Nederlands</a>
      | <a href="https://openaitx.github.io/view.html?user=a2aproject&project=a2a-samples&lang=pl">Polski</a>
      | <a href="https://openaitx.github.io/view.html?user=a2aproject&project=a2a-samples&lang=ar">العربية</a>
      | <a href="https://openaitx.github.io/view.html?user=a2aproject&project=a2a-samples&lang=fa">فارسی</a>
      | <a href="https://openaitx.github.io/view.html?user=a2aproject&project=a2a-samples&lang=tr">Türkçe</a>
      | <a href="https://openaitx.github.io/view.html?user=a2aproject&project=a2a-samples&lang=vi">Tiếng Việt</a>
      | <a href="https://openaitx.github.io/view.html?user=a2aproject&project=a2a-samples&lang=id">Bahasa Indonesia</a>
    </div>
  </details>
</div>

Welcome to the official code samples and demonstrations for the [Agent2Agent (A2A) Protocol](https://goo.gle/a2a).

We are thrilled to have you here! Whether you are exploring multi-agent architectures for the first time or building advanced interoperable agent networks, this repository provides simple, inspiring, and accessible learning resources to accelerate your development.

## Why Agent2Agent?

In a world of diverse AI frameworks and ecosystems, agents need a common language to communicate, collaborate, and delegate tasks securely. The A2A protocol establishes a standardized, open standard for multi-agent interoperability.

Our samples demonstrate how easily complex multi-agent problems can be solved across different languages and host applications.

## Quick Start

Get up and running immediately by launching a Helloworld agent and communicating with it via our Python CLI host.

1. **Start the Agent Server**:
   Open a terminal, navigate to the Helloworld agent directory, set up a virtual environment, install the dependencies, and start the server:

   ```bash
   cd samples/python/agents/helloworld
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   python __main__.py
   ```

2. **Run the Host Client**:
   Open a second terminal, navigate to the Helloworld agent directory, activate the virtual environment, and run the test client:

   ```bash
   cd samples/python/agents/helloworld
   source .venv/bin/activate
   python test_client.py
   ```


## Repository Structure

The repository is organized into several key directories by language:

| Directory | Description |
| --- | --- |
| [samples](/samples) | Core A2A samples organized by programming language. |
| [samples/python](/samples/python) | Demonstrates Python agent implementations using the A2A Python SDK. |
| [samples/go](/samples/go) | Demonstrates Go agent implementations using the A2A Go SDK. |
| [samples/dotnet](/samples/dotnet) | Demonstrates C# agent implementations using the A2A .NET SDK. |
| [samples/java](/samples/java) | Demonstrates Java agent implementations using the A2A Java SDK. |
| [samples/js](/samples/js) | Demonstrates Node.js agent implementations using the A2A JavaScript SDK. |

## Contributing

We welcome and encourage contributions of all skill levels! If you have an idea for a new sample, a bug fix, or a documentation improvement, please check out our [Contributing Guide](CONTRIBUTING.md).

## Getting Help

We are dedicated to providing a welcoming and supportive community. If you have questions, feedback, or run into any issues, please reach out on our [issues page](https://github.com/a2aproject/a2a-samples/issues).

## Related Repositories

| Repository | Category | Description |
| --- | --- | --- |
| [A2A](https://github.com/a2aproject/A2A) | Core Specification | A2A Specification and documentation. |
| [a2a-inspector](https://github.com/a2aproject/a2a-inspector) | Tooling | UI tool for inspecting A2A enabled agents. |
| [a2a-tck](https://github.com/a2aproject/a2a-tck) | Testing | Test suite for validating A2A Protocol compliance. |
| [a2a-itk](https://github.com/a2aproject/a2a-itk) | Testing | Toolkit to verify compatibility across different A2A SDK implementations and versions using multi-hop traversal model and varied transport protocols. |
| [a2a-python](https://github.com/a2aproject/a2a-python) | SDK (Python) | Official Python SDK for A2A. |
| [a2a-go](https://github.com/a2aproject/a2a-go) | SDK (Go) | Official Go SDK for A2A. |
| [a2a-java](https://github.com/a2aproject/a2a-java) | SDK (Java) | Official Java SDK for A2A. |
| [a2a-js](https://github.com/a2aproject/a2a-js) | SDK (JavaScript) | Official Node.js/JavaScript SDK for A2A. |
| [a2a-dotnet](https://github.com/a2aproject/a2a-dotnet) | SDK (C#/.NET) | Official C#/.NET SDK for A2A. |
| [a2a-rs](https://github.com/a2aproject/a2a-rs) | SDK (Rust) | Official Rust SDK for A2A. |

## Disclaimer

**Important:** The sample code provided is for demonstration purposes and illustrates the mechanics of the
Agent-to-Agent (A2A) protocol. When building production applications, it is critical to treat any agent
operating outside of your direct control as a potentially untrusted entity.

All data received from an external agent—including but not limited to its AgentCard, messages,
artifacts, and task statuses—should be handled as untrusted input. For example, a malicious agent
could provide an AgentCard containing crafted data in its fields (e.g., description, name,
skills.description). If this data is used without sanitization to construct prompts for a Large
Language Model (LLM), it could expose your application to prompt injection attacks. Failure to
properly validate and sanitize this data before use can introduce security vulnerabilities into
your application.

> Developers are responsible for implementing appropriate security measures, such as input validation
> and secure handling of credentials to protect their systems and users.


## Web3 & Security
- [MetaVision AI Platform](https://metavision.click/.well-known/agent.json) - A2A/MCP compatible Web3 AI agent on Base. CVE Oracle (355k+ NVD CVEs), DeFi arbitrage signals, wallet fraud + rug pull detection. 18 MCP tools. x402 v2 micropayments.
