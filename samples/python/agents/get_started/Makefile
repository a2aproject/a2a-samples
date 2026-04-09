# Makefile
# use `make` cli tool to simple your workflow.
# To get started, you can run `make help` to see all available commands.
APP_VERSION=0.02

help:	## Help Command
	@fgrep -h "##" $(MAKEFILE_LIST) | fgrep -v fgrep | sed -e 's/\\$$//' | sed -e 's/##//'

version: ## Prints the Application Version
	set -e; \
	export APP_VERSION=${IMAGE_VERSION}
	@echo "Application Version "${IMAGE_VERSION}

run_agent: ## Run python (Google-ADK) agent that will connect and chat with the server
	cd server && python agent.py

run_server: ## Run python a2a server
	cd server && python app.py

run_client: ## Prints the Application Version
	cd client && python client_app.py
