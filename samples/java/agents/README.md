# Sample Agents

All the agents in this directory are samples built on various frameworks highlighting various capabilities. Each agent runs as a standalone A2A server.

Each agent can be run as its own A2A server with the instructions in its README. By default, each will run on a separate port on localhost (you can override this behaviour).

## Agents Directory

* [**Quarkus LangChain4j Content Writer Agent**](content_writer/README.md)  
  Sample agent that generates an engaging piece of content given a content outline. To make use of this agent in a content creation multi-agent system, check out the [content_creation](../../python/hosts/content_creation/README.md) sample.

* [**Quarkus LangChain4j Content Editor Agent**](content_editor/README.md)  
  Sample agent to proof-read and polish content. To make use of this agent in a content creation multi-agent system, check out the [content_creation](../../python/hosts/content_creation/README.md) sample.

* [**Weather Agent**](weather_mcp/README.md)  
  Sample agent to provide weather information. To make use of this agent in a multi-language, multi-agent system, check out the [weather_and_airbnb_planner](../../python/hosts/weather_and_airbnb_planner/README.md) sample.

* [**Dice Agent (Multi-Transport)**](dice_agent_multi_transport/README.md)  
  Sample agent that can roll dice of different sizes and check if numbers are prime. This agent demonstrates
  multi-transport capabilities.

* [**Magic 8 Ball Agent (Security)**](magic_8_ball_security/README.md)  
  Sample agent that can respond to yes/no questions by consulting a Magic 8 Ball. This sample demonstrates how to secure an A2A server with Keycloak using bearer token authentication and it shows how to configure an A2A client to specify the token when sending requests.

## Disclaimer

Important: The sample code provided is for demonstration purposes and illustrates the
mechanics of the Agent-to-Agent (A2A) protocol. When building production applications,
it is critical to treat any agent operating outside of your direct control as a
potentially untrusted entity.

All data received from an external agent—including but not limited to its AgentCard,
messages, artifacts, and task statuses—should be handled as untrusted input. For
example, a malicious agent could provide an AgentCard containing crafted data in its
fields (e.g., description, name, skills.description). If this data is used without
sanitization to construct prompts for a Large Language Model (LLM), it could expose
your application to prompt injection attacks.  Failure to properly validate and
sanitize this data before use can introduce security vulnerabilities into your
application.

Developers are responsible for implementing appropriate security measures, such as
input validation and secure handling of credentials to protect their systems and users.
