# Copyright 2026 Saoussen Chaabnia
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

#!/usr/bin/env python3
"""
Deploy all 5 specialist agents to Cloud Run and collect their URLs
Supports parallel deployment for faster execution
"""

import asyncio
import os
import sys
from pathlib import Path

# Import env_utils from same directory
sys.path.insert(0, str(Path(__file__).parent))
import env_utils

# Agent configuration for deployment
AGENTS = [
    {
        "name": "brand-strategist",
        "dir": "brand_strategist",
        "port": 8080,
    },
    {
        "name": "copywriter",
        "dir": "copywriter",
        "port": 8080,
    },
    {
        "name": "designer",
        "dir": "designer",
        "port": 8080,
    },
    {
        "name": "critic",
        "dir": "critic",
        "port": 8080,
    },
    {
        "name": "project-manager",
        "dir": "project_manager",
        "port": 8080,
    },
]


async def run_command_async(cmd: list[str], cwd: Path | None = None) -> tuple[int, str, str]:
    """
    Run a command asynchronously

    Args:
        cmd: Command as list of strings
        cwd: Working directory for command

    Returns:
        Tuple of (returncode, stdout, stderr)
    """
    process = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, cwd=cwd
    )

    stdout, stderr = await process.communicate()
    return process.returncode, stdout.decode(), stderr.decode()


async def deploy_single_agent(agent_config: dict, project_id: str, region: str) -> str | None:
    """
    Deploy a single agent to Cloud Run

    Args:
        agent_config: Agent configuration dict
        project_id: GCP project ID
        region: GCP region

    Returns:
        Agent URL or None if deployment failed
    """
    name = agent_config["name"]
    agent_dir = agent_config["dir"]

    print(f"🚀 Deploying {name}...")

    # Build Cloud Run deployment command
    agent_path = Path(__file__).parent.parent / "agents" / agent_dir

    # Build environment variables
    env_vars = (
        f"GOOGLE_GENAI_USE_VERTEXAI=true,"
        f"GOOGLE_CLOUD_PROJECT={project_id},"
        f"GOOGLE_CLOUD_LOCATION={region}"
    )

    # Add Notion credentials for project-manager agent
    if name == "project-manager":
        notion_api_key = os.getenv("NOTION_API_KEY")
        notion_database_id = os.getenv("NOTION_DATABASE_ID")

        if notion_api_key and notion_database_id:
            print(f"   Adding Notion MCP credentials to {name}...")
            env_vars += f",NOTION_API_KEY={notion_api_key},NOTION_DATABASE_ID={notion_database_id}"
        else:
            print(
                f"   Warning: NOTION_API_KEY or NOTION_DATABASE_ID not set - {name} will work without Notion integration"
            )

    cmd = [
        "gcloud",
        "run",
        "deploy",
        name,
        "--source=.",
        "--port=8080",
        "--platform=managed",
        f"--region={region}",
        f"--project={project_id}",
        "--allow-unauthenticated",  # Allow public access to agent cards
        f"--set-env-vars={env_vars}",
        "--memory=1Gi",
        "--cpu=1",
        "--timeout=300",
        "--max-instances=10",
        "--min-instances=0",
        "--quiet",
    ]

    # Run deployment
    returncode, stdout, stderr = await run_command_async(cmd, cwd=agent_path)

    if returncode != 0:
        print(f"❌ Failed to deploy {name}")
        print(f"   Error: {stderr}")
        return None

    print(f"✓ {name} deployed successfully")

    # Get service URL
    url = await get_service_url(name, project_id, region)

    if url:
        # Update A2A configuration
        await update_agent_a2a_config(name, url, project_id, region)

    return url


async def get_service_url(service_name: str, project_id: str, region: str) -> str | None:
    """
    Get Cloud Run service URL after deployment

    Args:
        service_name: Name of the Cloud Run service
        project_id: GCP project ID
        region: GCP region

    Returns:
        Service URL or None if not found
    """
    cmd = [
        "gcloud",
        "run",
        "services",
        "describe",
        service_name,
        "--platform=managed",
        f"--region={region}",
        f"--project={project_id}",
        "--format=value(status.url)",
    ]

    returncode, stdout, stderr = await run_command_async(cmd)

    if returncode != 0:
        print(f"   Warning: Could not get URL for {service_name}")
        return None

    url = stdout.strip()
    print(f"   URL: {url}")
    return url


async def update_agent_a2a_config(
    service_name: str, url: str, project_id: str, region: str
) -> None:
    """
    Update deployed agent with A2A configuration (PUBLIC_HOST, PORT, PROTOCOL)
    Also adds Notion credentials for project-manager agent.

    Args:
        service_name: Name of the Cloud Run service
        url: Service URL
        project_id: GCP project ID
        region: GCP region
    """
    # Extract PUBLIC_HOST from URL (remove https:// and trailing path)
    public_host = url.replace("https://", "").replace("http://", "").split("/")[0]

    print(f"   Updating A2A config for {service_name}...")

    # Build environment variables update
    env_vars_update = f"PUBLIC_HOST={public_host},PUBLIC_PORT=443,PROTOCOL=https"

    # Add Notion credentials for project-manager agent
    if service_name == "project-manager":
        notion_api_key = os.getenv("NOTION_API_KEY")
        notion_database_id = os.getenv("NOTION_DATABASE_ID")

        if notion_api_key and notion_database_id:
            print(f"   Adding Notion MCP credentials to {service_name}...")
            env_vars_update += (
                f",NOTION_API_KEY={notion_api_key},NOTION_DATABASE_ID={notion_database_id}"
            )
        else:
            print(
                f"   Warning: NOTION_API_KEY or NOTION_DATABASE_ID not set - {service_name} will work without Notion integration"
            )

    cmd = [
        "gcloud",
        "run",
        "services",
        "update",
        service_name,
        "--platform=managed",
        f"--region={region}",
        f"--project={project_id}",
        f"--update-env-vars={env_vars_update}",
        "--quiet",
    ]

    returncode, stdout, stderr = await run_command_async(cmd)

    if returncode == 0:
        print(f"   ✓ A2A config updated for {service_name}")
    else:
        print(f"   Warning: Could not update A2A config for {service_name}: {stderr}")


async def deploy_all_agents(project_id: str, region: str) -> dict[str, str]:
    """
    Deploy all agents in parallel and collect their URLs

    Args:
        project_id: GCP project ID
        region: GCP region

    Returns:
        Dict mapping agent names to their URLs
    """
    print("\n" + "=" * 70)
    print("Deploying all specialist agents to Cloud Run (in parallel)")
    print("=" * 70 + "\n")

    # Deploy all agents in parallel using asyncio.gather
    tasks = [deploy_single_agent(agent, project_id, region) for agent in AGENTS]

    results = await asyncio.gather(*tasks)

    # Build URL mapping
    agent_urls = {}
    for agent, url in zip(AGENTS, results):
        if url:
            agent_urls[agent["name"]] = url
        else:
            print(f"⚠️  Warning: {agent['name']} deployment failed or URL not available")

    print("\n" + "=" * 70)
    print(f"✓ Deployment complete! {len(agent_urls)}/{len(AGENTS)} agents deployed")
    print("=" * 70 + "\n")

    # Display summary
    print("Agent URLs:")
    for name, url in agent_urls.items():
        print(f"  • {name}: {url}")

    return agent_urls


async def main_async():
    """Async main function"""
    print("Multi-Agent Cloud Run Deployment\n")

    # Load environment configuration
    config = env_utils.load_env_file()

    try:
        env_utils.validate_required_vars(config)
    except ValueError as e:
        print(f"Error: {e}")
        print("\nPlease set the required environment variables in .env file:")
        print("  GCP_PROJECT_ID - Your Google Cloud project ID")
        print("  GCP_REGION - Deployment region (default: us-central1)")
        sys.exit(1)

    project_id = config["PROJECT_ID"]
    region = config["REGION"]

    print(f"Project: {project_id}")
    print(f"Region: {region}\n")

    # Check if gcloud is installed
    try:
        returncode, _, _ = await run_command_async(["gcloud", "version"])
        if returncode != 0:
            raise FileNotFoundError
    except FileNotFoundError:
        print("Error: gcloud CLI not found")
        print("Please install from: https://cloud.google.com/sdk/docs/install")
        sys.exit(1)

    # Deploy all agents
    try:
        agent_urls = await deploy_all_agents(project_id, region)

        if not agent_urls:
            print("\n❌ No agents were deployed successfully")
            sys.exit(1)

        # Save URLs to file for orchestrator deployment
        env_utils.save_urls_to_env_file(agent_urls)

        print("\n✓ All specialist agents are ready!")
        print("  URLs saved to .env.specialists")

        return agent_urls

    except Exception as e:
        print(f"\n❌ Error during deployment: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


def main():
    """Main entry point"""
    return asyncio.run(main_async())


if __name__ == "__main__":
    main()
