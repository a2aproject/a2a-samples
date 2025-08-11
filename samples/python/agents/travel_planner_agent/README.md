# travel planner example
> This is a Python implementation that adheres to the A2A (Agent2Agent) protocol. 
> It is a travel assistant in line with the specifications of the OpenAI model, capable of providing you with travel planning services.
> A travel assistant demo implemented based on Google's official a2a-python SDK.

## Getting started

1. update [config.json](config.json) with your own OpenAI API key etc.
> You need to modify the values corresponding to model_name and base_url.

```json
{
  "model_name":"qwen3-32b", //defaults to gpt-4o if empty
  "api_key": "API_KEY",
  "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1" //defaults to ChatGPT if empty
}
```



2. Create an environment file with your API key:
> You need to set the value corresponding to API_KEY.

   ```bash
   echo "API_KEY=your_api_key_here" > .env
   ```


3. Start the server
    ```bash
    uv run .
    ```

4. Run the loop client
    ```bash
    uv run loop_client.py
    ```
   

## License

This project is licensed under the terms of the [Apache 2.0 License](/LICENSE).

## Contributing

See [CONTRIBUTING.md](/CONTRIBUTING.md) for contribution guidelines.



## Disclaimer
Important: The sample code provided is for demonstration purposes and illustrates the mechanics of the Agent-to-Agent (A2A) protocol. When building production applications, it is critical to treat any agent operating outside of your direct control as a potentially untrusted entity.

All data received from an external agent—including but not limited to its AgentCard, messages, artifacts, and task statuses—should be handled as untrusted input. For example, a malicious agent could provide an AgentCard containing crafted data in its fields (e.g., description, name, skills.description). If this data is used without sanitization to construct prompts for a Large Language Model (LLM), it could expose your application to prompt injection attacks.  Failure to properly validate and sanitize this data before use can introduce security vulnerabilities into your application.

Developers are responsible for implementing appropriate security measures, such as input validation and secure handling of credentials to protect their systems and users.