defmodule ItkElixirAgent.Application do
  @moduledoc false
  use Application

  require Logger

  @impl true
  def start(_type, _args) do
    http_port = get_port("ITK_HTTP_PORT", 10200)
    _grpc_port = get_port("ITK_GRPC_PORT", 11200)

    base_url = "http://127.0.0.1:#{http_port}/jsonrpc"

    router_opts = [
      agent_module: Itk.Agent,
      base_url: base_url
    ]

    children = [
      Itk.Agent,
      {Bandit, plug: {Itk.Router, router_opts}, port: http_port, startup_log: false}
    ]

    Logger.info("Starting ITK Elixir v1.0 Agent on HTTP port #{http_port}")
    Logger.info("Agent card: #{base_url}/.well-known/agent-card.json")

    Supervisor.start_link(children, strategy: :one_for_one, name: ItkElixirAgent.Supervisor)
  end

  defp get_port(env_var, default) do
    case System.get_env(env_var) do
      nil -> default
      val -> String.to_integer(val)
    end
  end
end
