# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
APP_VERSION=0.05.0

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
