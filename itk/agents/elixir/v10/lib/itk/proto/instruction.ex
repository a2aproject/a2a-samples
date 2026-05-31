defmodule Itk.Proto.SeriesOfSteps.ResponseGenerator do
  @moduledoc "Protobuf enum for SeriesOfSteps.ResponseGenerator"
  use Protobuf, enum: true, protoc_gen_elixir_version: "0.13.0", syntax: :proto3

  field :RESPONSE_GENERATOR_UNSPECIFIED, 0
  field :RESPONSE_GENERATOR_CONCAT, 1
end

defmodule Itk.Proto.ReturnResponse do
  @moduledoc "Protobuf definition for itk.ReturnResponse"
  use Protobuf, protoc_gen_elixir_version: "0.13.0", syntax: :proto3

  field :response, 1, type: :string
end

defmodule Itk.Proto.CallAgent do
  @moduledoc "Protobuf definition for itk.CallAgent"
  use Protobuf, protoc_gen_elixir_version: "0.13.0", syntax: :proto3

  field :transport, 1, type: :string
  field :agent_card_uri, 2, type: :string, json_name: "agentCardUri"
  field :instruction, 3, type: Itk.Proto.Instruction
  field :streaming, 4, type: :bool
end

defmodule Itk.Proto.SeriesOfSteps do
  @moduledoc "Protobuf definition for itk.SeriesOfSteps"
  use Protobuf, protoc_gen_elixir_version: "0.13.0", syntax: :proto3

  field :instructions, 1, repeated: true, type: Itk.Proto.Instruction
  field :response_generator, 2, type: Itk.Proto.SeriesOfSteps.ResponseGenerator, json_name: "responseGenerator", enum: true
end

defmodule Itk.Proto.Instruction do
  @moduledoc "Protobuf definition for itk.Instruction"
  use Protobuf, protoc_gen_elixir_version: "0.13.0", syntax: :proto3

  oneof :step, 0

  field :call_agent, 1, type: Itk.Proto.CallAgent, json_name: "callAgent", oneof: 0
  field :return_response, 2, type: Itk.Proto.ReturnResponse, json_name: "returnResponse", oneof: 0
  field :steps, 3, type: Itk.Proto.SeriesOfSteps, oneof: 0
end
