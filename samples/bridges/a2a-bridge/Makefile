PROJECT_ID      ?= my-gcp-project
REGION          ?= us-central1
LOCATION        ?= global
VERTEX_ENDPOINT ?= https://aiplatform.googleapis.com
CONFIG          ?= agents.json
SERVICE         ?= a2a-bridge
REPO            ?= a2a-bridge
IMAGE            = $(REGION)-docker.pkg.dev/$(PROJECT_ID)/$(REPO)/bridge:latest
BUCKET          ?= $(PROJECT_ID)-a2a-bridge
SERVICE_ACCOUNT ?= a2a-bridge@$(PROJECT_ID).iam.gserviceaccount.com
SRS_REGION      ?= us-central1

CLI = a2a-bridge \
  --project $(PROJECT_ID) \
  --location $(LOCATION) \
  --endpoint $(VERTEX_ENDPOINT) \
  --config $(CONFIG)

TF_VARS = \
  -var project_id=$(PROJECT_ID) \
  -var region=$(REGION) \
  -var vertex_endpoint=$(VERTEX_ENDPOINT)

.PHONY: install lint test serve card bootstrap \
        tf-init tf-plan tf-apply build deploy \
        setup-agent publish-skills sync-template register-ge smoke

install:
	pip install -e '.[dev]'

# One-shot quickstart: provision infra, build and deploy the image, then
# create the managed agent. Run after `pip install -e .[dev]` with:
#   make bootstrap PROJECT_ID=my-project AGENT_KEY=business-analyst
bootstrap: tf-init tf-apply build deploy setup-agent

lint:
	ruff check .
	mypy bridge cli

test:
	pytest -q

serve:
	PROJECT_ID=$(PROJECT_ID) AGENTS_CONFIG=$(CONFIG) \
	VERTEX_ENDPOINT=$(VERTEX_ENDPOINT) $(CLI) serve

card:
	$(CLI) card --url $(URL)

tf-init:
	terraform -chdir=terraform init

tf-plan:
	terraform -chdir=terraform plan $(TF_VARS)

tf-apply:
	terraform -chdir=terraform apply $(TF_VARS)

build:
	gcloud builds submit \
	  --config cloudbuild.yaml \
	  --substitutions _REGION=$(REGION),_REPO=$(REPO) \
	  --project $(PROJECT_ID) \
	  .

deploy:
	gcloud run deploy $(SERVICE) \
	  --image $(IMAGE) \
	  --region $(REGION) \
	  --project $(PROJECT_ID)

setup-agent:
	$(CLI) setup-agent \
	  --bucket $(BUCKET) \
	  --service-account $(SERVICE_ACCOUNT) \
	  $(if $(SKILL_REGISTRY_SOURCE),--skill-registry-source $(SKILL_REGISTRY_SOURCE)) \
	  $(if $(BODY_FILE),--body-file $(BODY_FILE)) \
	  $(if $(AGENT_KEY),--key $(AGENT_KEY))

publish-skills:
	$(CLI) publish-skills \
	  --dir agent-template/skills \
	  --region $(SRS_REGION) \
	  $(if $(SRS_ENDPOINT),--srs-endpoint $(SRS_ENDPOINT))

sync-template:
	$(CLI) sync-template --bucket $(BUCKET)

register-ge:
	$(CLI) register-ge \
	  --app $(GE_APP_ID) \
	  --url $(URL) \
	  $(if $(GE_AGENT_ID),--id $(GE_AGENT_ID)) \
	  $(if $(AGENT_KEY),--key $(AGENT_KEY)) \
	  $(if $(GE_AUTHZ),--authorization $(GE_AUTHZ)) \
	  $(if $(ICON_URL),--icon-url $(ICON_URL))

smoke:
	curl -fsS \
	  -H "X-Serverless-Authorization: Bearer $$(gcloud auth print-identity-token)" \
	  $(URL)/.well-known/agent-card.json | python3 -m json.tool
