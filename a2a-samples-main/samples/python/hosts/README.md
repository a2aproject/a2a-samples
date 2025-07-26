## Hosts

Sample apps or agents that are A2A clients that work with A2A servers. 

* [CLI](/samples/python/hosts/cli)  
  Command line tool to interact with an A2A server. Specify the server location on the command line. The CLI client looks up the agent card and then performs task completion in a loop based on command line inputs. 

* [Orchestrator Agent](/samples/python/hosts/multiagent)  
An Agent that speaks A2A and can delegate tasks to remote agents. Built on the Google ADK for demonstration purposes. Includes a "Host Agent" that maintains a collection of "Remote Agents". The Host Agent is itself an agent and can delegate tasks to one or more Remote Agents. Each RemoteAgent is an A2AClient that delegates to an A2A Server. 

* [MultiAgent Web Host](/demo/README.md)  
*This lives in the [demo](/demo/README.md) directory*  
A web app that visually shows A2A conversations with multiple agents (using the [Orchestrator Agent](/samples/python/hosts/multiagent)). Will render text, image, and webform artifacts. Has a separate tab to visualize task state and history as well as known agent cards. 


## Disclaimer
Important: The sample code provided is for demonstration purposes and illustrates the mechanics of the Agent-to-Agent (A2A) protocol. When building production applications, it is critical to treat any agent operating outside of your direct control as a potentially untrusted entity.

All data received from an external agent—including but not limited to its AgentCard, messages, artifacts, and task statuses—should be handled as untrusted input. For example, a malicious agent could provide an AgentCard containing crafted data in its fields (e.g., description, name, skills.description). If this data is used without sanitization to construct prompts for a Large Language Model (LLM), it could expose your application to prompt injection attacks.  Failure to properly validate and sanitize this data before use can introduce security vulnerabilities into your application.

Developers are responsible for implementing appropriate security measures, such as input validation and secure handling of credentials to protect their systems and users.