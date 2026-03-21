defmodule Itk.InstructionHandler do
  @moduledoc """
  Handles ITK protobuf instructions.

  This is a stateless module — all functions can be called from any process.
  This avoids GenServer deadlocks during multi-hop call chains.
  """

  require Logger

  @doc """
  Extracts and processes an instruction from a parsed message.
  Returns `{:ok, response_text}` or `{:error, reason}`.
  """
  def handle(message) do
    case extract_instruction(message) do
      {:ok, instruction} ->
        Logger.info("Processing instruction")
        results = handle_instruction(instruction)
        response_text = Enum.join(results, "\n")
        Logger.info("Response: #{response_text}")
        {:ok, response_text}

      {:error, reason} ->
        Logger.error("Failed to extract instruction: #{reason}")
        {:error, reason}
    end
  end

  # Extract protobuf instruction from message parts
  defp extract_instruction(%{parts: parts}) do
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

    # Build A2A v1.0 JSON-RPC request
    # Use proto enum names for roles and "raw" for binary parts
    message = %{
      "role" => "ROLE_USER",
      "messageId" => Itk.UUID.generate(),
      "parts" => [
        %{
          "raw" => b64,
          "mediaType" => "application/x-protobuf",
          "filename" => "instruction.bin"
        }
      ]
    }

    case send_a2a_message(uri, message) do
      {:ok, results} -> results
      {:error, reason} ->
        Logger.error("Failed to call agent at #{uri}: #{reason}")
        [reason]
    end
  end

  defp send_a2a_message(jsonrpc_url, message) do
    # Use v1.0 method name "SendMessage" (not v0.3 "message/send")
    request_body = %{
      "jsonrpc" => "2.0",
      "id" => Itk.UUID.generate(),
      "method" => "SendMessage",
      "params" => %{
        "message" => message
      }
    }

    Logger.info("Sending JSON-RPC to #{jsonrpc_url}")

    headers = [{"a2a-version", "1.0"}]

    case Req.post(jsonrpc_url, json: request_body, headers: headers, receive_timeout: 120_000) do
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
    # Try various response formats:
    # v1.0: result has id, contextId, status, history, artifacts
    # v0.3: result has task with similar structure
    message = find_agent_message(result)

    case message do
      %{"parts" => parts} when is_list(parts) ->
        extract_text_parts(parts)

      _ ->
        # Try artifacts
        artifacts = get_artifacts(result)
        case artifacts do
          [%{"parts" => parts} | _] when is_list(parts) ->
            extract_text_parts(parts)

          _ ->
            Logger.warning("Could not extract text from result: #{inspect(result)}")
            []
        end
    end
  end

  defp extract_texts_from_result(_), do: []

  defp find_agent_message(result) do
    cond do
      # Direct task with status.message
      is_map(result["status"]) and is_map(result["status"]["message"]) ->
        result["status"]["message"]

      # Task with history - get last agent message
      is_list(result["history"]) and length(result["history"]) > 0 ->
        result["history"]
        |> Enum.filter(fn msg ->
          role = Map.get(msg, "role")
          role in ["agent", "ROLE_AGENT"]
        end)
        |> List.last()

      # Direct message format
      is_list(result["parts"]) ->
        result

      # Wrapped in "task" key
      is_map(result["task"]) ->
        find_agent_message(result["task"])

      # Message wrapper (v1.0)
      is_map(result["message"]) ->
        result["message"]

      true ->
        nil
    end
  end

  defp get_artifacts(result) do
    case result do
      %{"artifacts" => artifacts} when is_list(artifacts) -> artifacts
      %{"task" => %{"artifacts" => artifacts}} when is_list(artifacts) -> artifacts
      _ -> []
    end
  end

  defp extract_text_parts(parts) do
    Enum.flat_map(parts, fn
      %{"text" => text} when is_binary(text) -> [text]
      %{"kind" => "text", "text" => text} when is_binary(text) -> [text]
      %{"root" => %{"text" => text}} when is_binary(text) -> [text]
      _ -> []
    end)
  end
end
