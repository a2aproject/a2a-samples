defmodule Itk.Router do
  @moduledoc """
  Custom Plug that serves agent card and handles JSON-RPC requests
  directly — without going through the A2A.Agent GenServer — to avoid
  deadlocks during multi-hop call chains.

  Each HTTP request is processed in its own Bandit handler process,
  so concurrent inbound calls don't block each other.

  Supports both regular (SendMessage) and streaming (SendStreamingMessage)
  requests. Streaming responses use Server-Sent Events (SSE) with
  `text/event-stream` content type.
  """

  @behaviour Plug
  import Plug.Conn

  require Logger

  @impl Plug
  def init(opts) do
    %{
      base_url: Keyword.fetch!(opts, :base_url),
      agent_module: Keyword.fetch!(opts, :agent_module)
    }
  end

  @impl Plug
  # Agent card
  def call(%{method: "GET", path_info: ["jsonrpc", ".well-known", "agent-card.json"]} = conn, opts) do
    card = opts.agent_module.agent_card()

    json =
      A2A.JSON.encode_agent_card(card,
        url: opts.base_url,
        capabilities: %{},
        supported_interfaces: [
          %{url: opts.base_url, protocol_binding: "JSONRPC", protocol_version: "1.0"}
        ]
      )

    conn
    |> put_resp_content_type("application/json")
    |> send_resp(200, Jason.encode!(json))
  end

  # JSON-RPC endpoint
  def call(%{method: "POST", path_info: ["jsonrpc"]} = conn, _opts) do
    {:ok, body, conn} = Plug.Conn.read_body(conn)

    case Jason.decode(body) do
      {:ok, decoded} ->
        handle_jsonrpc(conn, decoded)

      {:error, _} ->
        conn
        |> put_resp_content_type("application/json")
        |> send_resp(200, Jason.encode!(jsonrpc_error(nil, -32700, "Parse error")))
    end
  end

  def call(conn, _opts) do
    send_resp(conn, 404, "Not Found")
  end

  # --- JSON-RPC dispatch ---

  defp handle_jsonrpc(conn, %{"method" => method, "id" => id, "params" => params}) do
    case method do
      # v1.0 streaming
      "SendStreamingMessage" ->
        handle_streaming_message(conn, id, params)

      # v0.3 streaming
      "message/stream" ->
        handle_streaming_message(conn, id, params)

      # v1.0 method names — wrapped response
      "SendMessage" ->
        response = handle_send_message(id, params, :v10)
        json_response(conn, response)

      # v0.3 compat — flat response
      "message/send" ->
        response = handle_send_message(id, params, :v03)
        json_response(conn, response)

      "GetTask" ->
        json_response(conn, handle_get_task(id, params))

      "tasks/get" ->
        json_response(conn, handle_get_task(id, params))

      "ListTasks" ->
        json_response(conn, jsonrpc_response(id, %{"tasks" => []}))

      "tasks/list" ->
        json_response(conn, jsonrpc_response(id, %{"tasks" => []}))

      "CancelTask" ->
        json_response(conn, jsonrpc_error(id, -32001, "Task not found"))

      "tasks/cancel" ->
        json_response(conn, jsonrpc_error(id, -32001, "Task not found"))

      _ ->
        json_response(conn, jsonrpc_error(id, -32601, "Method not found"))
    end
  end

  defp handle_jsonrpc(conn, %{"id" => id}) do
    json_response(conn, jsonrpc_error(id, -32600, "Invalid Request"))
  end

  defp handle_jsonrpc(conn, _) do
    json_response(conn, jsonrpc_error(nil, -32600, "Invalid Request"))
  end

  # --- Regular message handling ---

  defp handle_send_message(id, %{"message" => message_map}, version) do
    message = parse_message(message_map)

    case Itk.InstructionHandler.handle(message) do
      {:ok, response_text} ->
        context_id = Map.get(message_map, "contextId", Itk.UUID.generate())

        result =
          case version do
            :v10 ->
              %{
                "message" => %{
                  "role" => "ROLE_AGENT",
                  "messageId" => Itk.UUID.generate(),
                  "parts" => [%{"text" => response_text}],
                  "contextId" => context_id
                }
              }

            :v03 ->
              %{
                "role" => "agent",
                "messageId" => Itk.UUID.generate(),
                "parts" => [%{"text" => response_text}],
                "contextId" => context_id
              }
          end

        %{"jsonrpc" => "2.0", "id" => id, "result" => result}

      {:error, reason} ->
        jsonrpc_error(id, -32000, "Instruction error: #{reason}")
    end
  end

  defp handle_send_message(id, _params, _version) do
    jsonrpc_error(id, -32602, "Invalid params: missing 'message'")
  end

  # --- Streaming message handling (SSE) ---

  defp handle_streaming_message(conn, id, %{"message" => message_map}) do
    message = parse_message(message_map)
    context_id = Map.get(message_map, "contextId", Itk.UUID.generate())
    task_id = Itk.UUID.generate()

    # Start chunked SSE response
    conn =
      conn
      |> put_resp_content_type("text/event-stream")
      |> put_resp_header("cache-control", "no-cache")
      |> put_resp_header("connection", "keep-alive")
      |> send_chunked(200)

    # Send initial status: submitted
    conn = send_sse_status(conn, id, task_id, context_id, "submitted", false)

    # Send working status
    conn = send_sse_status(conn, id, task_id, context_id, "working", false)

    # Process instruction
    case Itk.InstructionHandler.handle(message) do
      {:ok, response_text} ->
        # Send artifact update
        conn = send_sse_artifact(conn, id, task_id, context_id, response_text)

        # Send completed status with message (final=true)
        conn =
          send_sse_status_with_message(
            conn,
            id,
            task_id,
            context_id,
            "completed",
            true,
            response_text
          )

        conn

      {:error, reason} ->
        error_text = "Instruction error: #{reason}"

        conn =
          send_sse_status_with_message(
            conn,
            id,
            task_id,
            context_id,
            "failed",
            true,
            error_text
          )

        conn
    end
  end

  defp handle_streaming_message(conn, id, _params) do
    conn =
      conn
      |> put_resp_content_type("text/event-stream")
      |> put_resp_header("cache-control", "no-cache")
      |> put_resp_header("connection", "keep-alive")
      |> send_chunked(200)

    error_result = %{
      "jsonrpc" => "2.0",
      "id" => id,
      "error" => %{"code" => -32602, "message" => "Invalid params: missing 'message'"}
    }

    chunk(conn, "data: #{Jason.encode!(error_result)}\n\n")
    conn
  end

  # --- SSE helpers ---
  # Format: flat events with `kind` discriminator, lowercase states
  # Matches pydantic SDK (a2a-sdk 0.3.x) expected format

  defp send_sse_status(conn, id, task_id, context_id, state, final) do
    result = %{
      "kind" => "status-update",
      "taskId" => task_id,
      "contextId" => context_id,
      "final" => final,
      "status" => %{
        "state" => state,
        "timestamp" => DateTime.utc_now() |> DateTime.to_iso8601()
      }
    }

    send_sse_chunk(conn, id, result)
  end

  defp send_sse_status_with_message(conn, id, task_id, context_id, state, final, text) do
    result = %{
      "kind" => "status-update",
      "taskId" => task_id,
      "contextId" => context_id,
      "final" => final,
      "status" => %{
        "state" => state,
        "timestamp" => DateTime.utc_now() |> DateTime.to_iso8601(),
        "message" => %{
          "kind" => "message",
          "role" => "agent",
          "messageId" => Itk.UUID.generate(),
          "parts" => [%{"kind" => "text", "text" => text}]
        }
      }
    }

    send_sse_chunk(conn, id, result)
  end

  defp send_sse_artifact(conn, id, task_id, context_id, text) do
    result = %{
      "kind" => "artifact-update",
      "taskId" => task_id,
      "contextId" => context_id,
      "artifact" => %{
        "artifactId" => Itk.UUID.generate(),
        "parts" => [%{"kind" => "text", "text" => text}]
      },
      "lastChunk" => true
    }

    send_sse_chunk(conn, id, result)
  end

  defp send_sse_chunk(conn, id, result) do
    payload = %{
      "jsonrpc" => "2.0",
      "id" => id,
      "result" => result
    }

    case chunk(conn, "data: #{Jason.encode!(payload)}\n\n") do
      {:ok, conn} -> conn
      {:error, _reason} -> conn
    end
  end

  # --- GetTask ---

  defp handle_get_task(id, %{"id" => _task_id}) do
    jsonrpc_error(id, -32001, "Task not found")
  end

  defp handle_get_task(id, _) do
    jsonrpc_error(id, -32602, "Invalid params")
  end

  # --- Helpers ---

  defp json_response(conn, response) do
    conn
    |> put_resp_content_type("application/json")
    |> send_resp(200, Jason.encode!(response))
  end

  defp parse_message(message_map) do
    parts = Map.get(message_map, "parts", [])

    parsed_parts =
      Enum.map(parts, fn
        # v1.0 format: raw bytes with mediaType/filename
        %{"raw" => raw_b64} = part when is_binary(raw_b64) ->
          %A2A.Part.File{
            file: %A2A.FileContent{
              bytes: Base.decode64!(raw_b64),
              mime_type: Map.get(part, "mediaType", "application/octet-stream"),
              name: Map.get(part, "filename")
            }
          }

        # v0.3 format: file wrapper
        %{"file" => %{"bytes" => bytes} = file} ->
          %A2A.Part.File{
            file: %A2A.FileContent{
              bytes: Base.decode64!(bytes),
              mime_type: Map.get(file, "mimeType", "application/octet-stream"),
              name: Map.get(file, "name")
            }
          }

        # Text part (v1.0 or v0.3)
        %{"text" => text} ->
          %A2A.Part.Text{text: text}

        %{"kind" => "text", "text" => text} ->
          %A2A.Part.Text{text: text}

        other ->
          Logger.warning("Unknown part type: #{inspect(other)}")
          nil
      end)
      |> Enum.reject(&is_nil/1)

    %{parts: parsed_parts}
  end

  defp jsonrpc_response(id, result) do
    %{
      "jsonrpc" => "2.0",
      "id" => id,
      "result" => result
    }
  end

  defp jsonrpc_error(id, code, message) do
    %{
      "jsonrpc" => "2.0",
      "id" => id,
      "error" => %{
        "code" => code,
        "message" => message
      }
    }
  end
end
