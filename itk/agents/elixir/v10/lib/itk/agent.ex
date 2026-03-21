defmodule Itk.Agent do
  @moduledoc """
  ITK v1.0 Agent card definition.

  The actual message handling is done by Itk.InstructionHandler (called
  from Itk.Router) to avoid GenServer deadlocks during multi-hop chains.
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

  @impl A2A.Agent
  def handle_message(_message, _context) do
    # Not used — Itk.Router handles messages directly
    {:error, "Use Itk.Router for message handling"}
  end
end
