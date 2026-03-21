defmodule Itk.Agent do
  @moduledoc """
  ITK v1.0 Agent for A2A Integration Test Kit.

  Receives protobuf-encoded instructions via A2A messages and processes them:
  - ReturnResponse: returns the specified text
  - CallAgent: calls another agent via A2A and returns the response
  - SeriesOfSteps: executes steps in order and concatenates results
  """

  use A2A.Agent,
    name: "ITK Elixir v1.0 Agent",
    description: "Elixir agent using A2A SDK 1.0 for ITK interop testing.",
    version: "1.0.0",
    skills: [
      %{
        id: "itk",
        name: "ITK",
        description: "Handles ITK multi-hop traversal instructions",
        tags: ["a2a", "interop", "itk"]
      }
    ]

  require Logger

  @impl A2A.Agent
  def handle_message(message, _context) do
    case extract_instruction(message) do
      {:ok, instruction} ->
        Logger.info("Processing instruction")
        results = handle_instruction(instruction)
        response_text = Enum.join(results, "\n")
        Logger.info("Response: #{response_text}")
        {:reply, [A2A.Part.Text.new(response_text)]}

      {:error, reason} ->
        Logger.error("Failed to extract instruction: #{reason}")
        {:error, reason}
    end
  end

  @impl A2A.Agent
  def handle_cancel(_context), do: :ok

  # Extract protobuf instruction from A2A message parts
  defp extract_instruction(message) do
    parts = Map.get(message, :parts, [])

    Enum.reduce_while(parts, {:error, "no instruction found"}, fn part, _acc ->
      case try_parse_instruction(part) do
        {:ok, inst} -> {:halt, {:ok, inst}}
        :skip -> {:cont, {:error, "no instruction found"}}
      end
    end)
  end

  defp try_parse_instruction(%A2A.Part.File{file: %A2A.FileContent{bytes: bytes}})
       when is_binary(bytes) and byte_size(bytes) > 0 do
    try do
      inst = Itk.Proto.Instruction.decode(bytes)
      {:ok, inst}
    rescue
      _ -> :skip
    end
  end

  defp try_parse_instruction(%A2A.Part.Text{text: text})
       when is_binary(text) and text != "" do
    try do
      raw = Base.decode64!(text)
      inst = Itk.Proto.Instruction.decode(raw)
      {:ok, inst}
    rescue
      _ -> :skip
    end
  end

  defp try_parse_instruction(_), do: :skip

  # Handle instruction types
  defp handle_instruction(%Itk.Proto.Instruction{step: {:return_response, %{response: response}}}) do
    [response]
  end

  defp handle_instruction(%Itk.Proto.Instruction{step: {:call_agent, call}}) do
    handle_call_agent(call)
  end

  defp handle_instruction(%Itk.Proto.Instruction{step: {:steps, series}}) do
    handle_series(series)
  end

  defp handle_instruction(other) do
    Logger.warning("Unknown instruction type: #{inspect(other)}")
    ["error: unknown instruction"]
  end

  # Execute a series of steps and concatenate results
  defp handle_series(%Itk.Proto.SeriesOfSteps{instructions: instructions}) do
    Enum.flat_map(instructions, &handle_instruction/1)
  end

  # Call another agent via A2A
  defp handle_call_agent(%Itk.Proto.CallAgent{
         agent_card_uri: uri,
         transport: transport,
         instruction: nested_instruction,
         streaming: streaming
       }) do
    Logger.info("Calling agent at #{uri} via #{transport} (streaming=#{streaming})")

    # Serialize the nested instruction back to protobuf, then base64 encode
    inst_bytes = Itk.Proto.Instruction.encode(nested_instruction)
    b64 = Base.encode64(inst_bytes)

    # Build A2A JSON-RPC request
    message = %{
      "role" => "user",
      "messageId" => Itk.UUID.generate(),
      "parts" => [
        %{
          "file" => %{
            "bytes" => b64,
            "mimeType" => "application/x-protobuf",
            "name" => "instruction.bin"
          }
        }
      ]
    }

    case send_a2a_message(uri, message) do
      {:ok, results} -> results
      {:error, reason} ->
        Logger.error("Failed to call agent at #{uri}: #{reason}")
        ["error: #{reason}"]
    end
  end

  defp send_a2a_message(jsonrpc_url, message) do
    request_body = %{
      "jsonrpc" => "2.0",
      "id" => Itk.UUID.generate(),
      "method" => "message/send",
      "params" => %{
        "message" => message
      }
    }

    Logger.info("Sending JSON-RPC to #{jsonrpc_url}")

    case Req.post(jsonrpc_url, json: request_body, receive_timeout: 120_000) do
      {:ok, %{status: 200, body: body}} ->
        extract_response_text(body)

      {:ok, %{status: status, body: body}} ->
        {:error, "HTTP #{status}: #{inspect(body)}"}

      {:error, reason} ->
        {:error, "request failed: #{inspect(reason)}"}
    end
  end

  defp extract_response_text(%{"result" => result}) do
    texts = extract_texts_from_result(result)
    {:ok, texts}
  end

  defp extract_response_text(%{"error" => error}) do
    {:error, "JSON-RPC error: #{inspect(error)}"}
  end

  defp extract_response_text(other) do
    {:error, "unexpected response: #{inspect(other)}"}
  end

  defp extract_texts_from_result(result) when is_map(result) do
    # Try task format: result.status.message.parts
    # Or message format: result.parts
    message =
      case result do
        %{"status" => %{"message" => msg}} -> msg
        %{"parts" => _} = msg -> msg
        _ -> nil
      end

    case message do
      %{"parts" => parts} when is_list(parts) ->
        Enum.flat_map(parts, fn
          %{"text" => text} when is_binary(text) -> [text]
          _ -> []
        end)

      _ ->
        Logger.warning("Could not extract text from result: #{inspect(result)}")
        []
    end
  end

  defp extract_texts_from_result(_), do: []
end
