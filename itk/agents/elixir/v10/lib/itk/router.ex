defmodule Itk.Router do
  @moduledoc """
  Custom Plug that serves agent card and handles JSON-RPC requests
  directly — without going through the A2A.Agent GenServer — to avoid
  deadlocks during multi-hop call chains.

  Each HTTP request is processed in its own Bandit handler process,
  so concurrent inbound calls don't block each other.
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
        response = handle_jsonrpc(decoded)

        conn
        |> put_resp_content_type("application/json")
        |> send_resp(200, Jason.encode!(response))

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

  defp handle_jsonrpc(%{"method" => method, "id" => id, "params" => params}) do
    case method do
      # v1.0 method names — wrapped response
      "SendMessage" ->
        handle_send_message(id, params, :v10)

      # v0.3 compat — flat response
      "message/send" ->
        handle_send_message(id, params, :v03)

      "GetTask" ->
        handle_get_task(id, params)

      "tasks/get" ->
        handle_get_task(id, params)

      "ListTasks" ->
        jsonrpc_response(id, %{"tasks" => []})

      "tasks/list" ->
        jsonrpc_response(id, %{"tasks" => []})

      "CancelTask" ->
        jsonrpc_error(id, -32001, "Task not found")

      "tasks/cancel" ->
        jsonrpc_error(id, -32001, "Task not found")

      _ ->
        jsonrpc_error(id, -32601, "Method not found")
    end
  end

  defp handle_jsonrpc(%{"id" => id}) do
    jsonrpc_error(id, -32600, "Invalid Request")
  end

  defp handle_jsonrpc(_) do
    jsonrpc_error(nil, -32600, "Invalid Request")
  end

  # --- Message handling (runs in the Bandit handler process, not the GenServer) ---

  defp handle_send_message(id, %{"message" => message_map}, version) do
    # Parse the message parts
    message = parse_message(message_map)

    case Itk.InstructionHandler.handle(message) do
      {:ok, response_text} ->
        context_id = Map.get(message_map, "contextId", Itk.UUID.generate())

        result =
          case version do
            # v1.0: wrap in "message" key with proto enum names
            :v10 ->
              %{
                "message" => %{
                  "role" => "ROLE_AGENT",
                  "messageId" => Itk.UUID.generate(),
                  "parts" => [%{"text" => response_text}],
                  "contextId" => context_id
                }
              }

            # v0.3: flat with lowercase role names
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

  defp handle_get_task(id, %{"id" => _task_id}) do
    # We don't store tasks — always return not found
    jsonrpc_error(id, -32001, "Task not found")
  end

  defp handle_get_task(id, _) do
    jsonrpc_error(id, -32602, "Invalid params")
  end

  # --- Helpers ---

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
