defmodule ItkElixirAgent.MixProject do
  use Mix.Project

  def project do
    [
      app: :itk_elixir_agent,
      version: "0.1.0",
      elixir: "~> 1.15",
      start_permanent: Mix.env() == :prod,
      deps: deps()
    ]
  end

  def application do
    [
      extra_applications: [:logger],
      mod: {ItkElixirAgent.Application, []}
    ]
  end

  defp deps do
    [
      # A2A Elixir SDK
      {:a2a, github: "zeroasterisk/a2a-elixir-1", branch: "combined-v1"},
      # HTTP client for outbound A2A calls
      {:req, "~> 0.5"},
      # JSON
      {:jason, "~> 1.4"},
      # Protobuf for ITK instruction parsing
      {:protobuf, "~> 0.13"},
      # Web server (pulled in by a2a)
      {:bandit, "~> 1.0"}
    ]
  end
end
