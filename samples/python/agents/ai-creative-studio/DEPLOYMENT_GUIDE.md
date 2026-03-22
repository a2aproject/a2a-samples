# AI Creative Studio - Complete Deployment Guide

> Step-by-step guide to deploy the distributed multi-agent system to Google Cloud

## 📋 Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Initial Setup](#initial-setup)
- [Notion Database Setup](#notion-database-setup)
- [Deployment Steps](#deployment-steps)
- [Testing Your Deployment](#testing-your-deployment)
- [Troubleshooting](#troubleshooting)
- [Updating Agents](#updating-agents)

---

## Overview

This guide walks you through deploying the AI Creative Studio, a distributed multi-agent system that includes:

- **5 Specialist Agents** → Deployed to **Cloud Run**
  - Brand Strategist
  - Copywriter
  - Designer
  - Critic
  - Project Manager

- **1 Orchestrator Agent** → Deployed to **Vertex AI Agent Engine**
  - Creative Director

**Deployment Time**: ~15-20 minutes for complete system

---

## Prerequisites

### 1. Google Cloud Setup

- **Google Cloud Project** with billing enabled
- **Project ID** and **Region** (recommended: `us-central1`)
- **gcloud CLI** installed and authenticated

```bash
# Install gcloud CLI (if not already installed)
# See: https://cloud.google.com/sdk/docs/install

# Authenticate
gcloud auth login

# Set your project
gcloud config set project YOUR_PROJECT_ID

# Enable required APIs
gcloud services enable \
  run.googleapis.com \
  aiplatform.googleapis.com \
  cloudbuild.googleapis.com \
  containerregistry.googleapis.com \
  compute.googleapis.com
```

### 2. Development Environment

- **Python 3.11+**
- **Node.js 20+** and **npm** (for Notion MCP server)
- **Docker** (for building container images)
- **Git** (for cloning the repository)

```bash
# Verify installations
python3 --version  # Should be 3.11 or higher
node --version     # Should be v20 or higher
npm --version
docker --version
gcloud --version
```

### 3. API Keys

**Google Gemini API Key:**
- Get from [Google AI Studio](https://aistudio.google.com/app/apikey)
- Free tier available
- Required for all agents

### 4. Notion Setup (Optional - for Project Manager)

**Only needed if you want Project Manager to create tasks in Notion**

1. **Create Notion Integration:**
   - Go to [Notion Developers](https://www.notion.so/my-integrations)
   - Click "New integration"
   - Give it a name (e.g., "AI Creative Studio")
   - Copy the **Integration Token** (starts with `ntn_`)

2. **Create TWO Notion Databases with Dynamic Schema Support:**

   The Project Manager uses **dynamic schema discovery** - it will automatically detect and use whatever property names you choose!

   **Projects Database:**
   - Create a new database in Notion
   - Add properties with these **types** (names can be anything you want):
     - One **Title** property (e.g., "Project name", "Name", "Title", etc.)
     - One **Status** property (e.g., "Status", "État", "Progress", etc.)
     - One **Select** property for priority (e.g., "Priority", "Priorité", etc.) - optional
     - One **Date** property with start & end enabled (e.g., "Dates", "Timeline", "Période", etc.)
     - One **Rich Text** property for summary (e.g., "Summary", "Description", etc.) - optional
   - Share with your integration (click "..." → Connections → Add integration)
   - Copy the database ID from URL: `notion.so/workspace/DATABASE_ID?v=...`
   - **The agent will discover your exact property names automatically!**

   **Tasks Database:**
   - Create another database
   - Add properties with these **types** (names can be anything you want):
     - One **Title** property (e.g., "Task name", "Tâche", "Task", etc.)
     - One **Status** property (e.g., "Status", "État", etc.)
     - One **Select** property for priority (e.g., "Priority", "Priorité", etc.) - optional
     - One **Date** property (e.g., "Due", "Deadline", "Due date", etc.)
     - One **Relation** property → select your Projects database (e.g., "Project", "Related project", etc.)
   - Share with your integration
   - Copy the database ID
   - **The agent will discover your exact property names automatically!**

---

## Initial Setup

### 0. Automated GCP Setup (Recommended)

For a quick automated setup of GCP infrastructure:

```bash
# Run the automated GCP setup script
./deploy/setup_gcp.sh
```

This script will:
- Enable required Google Cloud APIs
- Create service accounts for all agents
- Grant necessary IAM permissions

**Alternative**: Manual setup following steps below

### 1. Clone and Install Dependencies

```bash
# Clone the repository
git clone https://github.com/your-username/ai-creative-studio.git
cd ai-creative-studio

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your values
nano .env  # or use your preferred editor
```

**Required Configuration:**

```bash
# Google Cloud
GOOGLE_GENAI_USE_VERTEXAI=TRUE
PROJECT_ID=your-project-id
LOCATION=us-central1

# Gemini API
GOOGLE_API_KEY=your-gemini-api-key

# Notion Integration (Optional - for Project Manager)
# You need TWO databases:
# 1. Projects Database (provide ID here)
# 2. Tasks Database (update hardcoded ID in agents/project_manager/agent.py:59)
NOTION_API_KEY=your-notion-integration-token
NOTION_DATABASE_ID=your-projects-database-id

# Agent URLs (will be auto-filled during deployment)
STRATEGIST_AGENT_URL=
COPYWRITER_AGENT_URL=
DESIGNER_AGENT_URL=
CRITIC_AGENT_URL=
PM_AGENT_URL=

# Agent Engine (will be auto-filled during deployment)
AGENT_ENGINE_RESOURCE_NAME=
AGENT_ENGINE_ID=
```

### 3. Update Notion Tasks Database ID (if using Notion)

If you're using Notion integration, update the Tasks database ID:

```bash
# Edit the Project Manager agent
nano agents/project_manager/agent.py

# Find line 59 and replace with your Tasks database ID:
# **TASKS DATABASE ID: your_tasks_database_id_here**
```

---

## Deployment Steps

### Option 1: Complete Deployment (Recommended)

Deploy everything with a single command:

```bash
cd deploy
./deploy_complete_system.sh
```

This script:
1. ✅ Deploys all 5 specialist agents to Cloud Run (parallel deployment)
2. ✅ Collects agent URLs automatically
3. ✅ Deploys Creative Director to Agent Engine with URLs
4. ✅ Updates your `.env` file with URLs and resource names

**Time**: ~10-15 minutes

**What happens:**
- Builds Docker images for each specialist agent
- Pushes images to Google Container Registry
- Deploys to Cloud Run with environment variables
- Deploys orchestrator to Vertex AI Agent Engine
- Outputs complete configuration

**Expected Output:**
```
🚀 Deploying AI Creative Studio
================================

Step 1: Deploying specialist agents to Cloud Run...
  ✓ Brand Strategist deployed: https://brand-strategist-xxxxx-uc.a.run.app
  ✓ Copywriter deployed: https://copywriter-xxxxx-uc.a.run.app
  ✓ Designer deployed: https://designer-xxxxx-uc.a.run.app
  ✓ Critic deployed: https://critic-xxxxx-uc.a.run.app
  ✓ Project Manager deployed: https://project-manager-xxxxx-uc.a.run.app

Step 2: Deploying Creative Director to Agent Engine...
  ✓ Orchestrator deployed: projects/123/locations/us-central1/reasoningEngines/456

✅ Deployment Complete!

Next steps:
Test deployment: ./test_agents.sh orchestrator
```

---

### Option 2: Manual Step-by-Step Deployment

If you prefer more control:

#### Step 1: Deploy Specialist Agents

```bash
cd deploy
python3 deploy_all_specialists.py
```

This deploys all 5 agents to Cloud Run in parallel.

**What it does:**
- Builds Docker images for each agent
- Pushes to Google Container Registry
- Deploys to Cloud Run with:
  - `GOOGLE_API_KEY` (all agents)
  - `NOTION_API_KEY` (Project Manager only)
  - `NOTION_DATABASE_ID` (Project Manager only)
- Returns agent URLs

**Copy the URLs** and update your `.env`:

```bash
STRATEGIST_AGENT_URL="https://brand-strategist-xxxxx-uc.a.run.app"
COPYWRITER_AGENT_URL="https://copywriter-xxxxx-uc.a.run.app"
DESIGNER_AGENT_URL="https://designer-xxxxx-uc.a.run.app"
CRITIC_AGENT_URL="https://critic-xxxxx-uc.a.run.app"
PM_AGENT_URL="https://project-manager-xxxxx-uc.a.run.app"
```

#### Step 2: Deploy Creative Director (Orchestrator)

```bash
cd ../deploy
python3 deploy_orchestrator.py --action deploy
```

This deploys the Creative Director to Vertex AI Agent Engine with all specialist URLs.

**Copy the resource name** and update your `.env`:

```bash
AGENT_ENGINE_RESOURCE_NAME="projects/123/locations/us-central1/reasoningEngines/456"
```

---

### Option 3: Deploy Individual Agent

To deploy or update a single agent:

```bash
cd deploy
./deploy.sh

# Follow prompts to select agent directory
```

Or directly:

```bash
cd agents/brand_strategist
docker build -t brand-strategist .
gcloud run deploy brand-strategist-agent \
  --image brand-strategist \
  --region us-central1 \
  --platform managed \
  --set-env-vars GOOGLE_API_KEY=$GOOGLE_API_KEY
```

---

## Testing Your Deployment

### Step 1: Test Individual Specialist Agents

```bash
cd deploy
./test_agents.sh specialists
```

This tests each specialist agent individually to verify they're working.

**Expected Output:**
```
Testing Brand Strategist...
  ✓ Agent accessible
  ✓ Response received
  ✓ Market research completed

Testing Copywriter...
  ✓ Agent accessible
  ✓ Response received
  ✓ Instagram posts created

[... etc for all agents ...]
```

### Step 2: Test Creative Director Orchestrator

```bash
./test_agents.sh orchestrator
```

This tests the complete workflow with the orchestrator calling all 5 specialists.

**Expected Output:**
```
Testing Creative Director Orchestrator...
  ✓ Connected to Agent Engine
  ✓ Session created

  I'll coordinate our team to create your complete social media campaign:

  1. Brand Strategist will research the market
  2. Copywriter will create 3 Instagram posts
  3. Designer will generate image concepts
  4. Critic will review quality
  5. Project Manager will create timeline

  [... complete campaign output ...]

  ✓ All 5 agents called successfully!
```

### Step 3: Test Complete System

```bash
./test_agents.sh all
```

This runs all tests: specialists + orchestrator.

---

## Troubleshooting

### Issue 1: "Brand Strategist returned empty response"


---

### Issue 2: Orchestrator Stops After 2-3 Agents

**Symptom**: Orchestrator completes brand_strategist, copywriter, and designer, but stops before calling critic and project_manager

**Root Cause**: Token output limit reached. The orchestrator was hitting the 8192 token limit before completing all 5 agents.

**Solution**: The latest version includes **lazy context compaction** that prevents this issue:

```python
# In agents/creative_director/agent.py

# Increased token limit
max_output_tokens=20000  # Was 8192

# Lazy context compaction
compaction_config = EventsCompactionConfig(
    compaction_interval=3,  # Summarize after every 3 agents
    overlap_size=1,         # Keep most recent agent's full output
    summarizer=LlmEventSummarizer(llm=Gemini(model_id="gemini-2.5-flash"))
)
```

**How it works**:
1. **Agents 1-3** (Strategist → Copywriter → Designer): Full context preserved
2. **After Agent 3**: Context compacted → Agents 1-2 summarized, Agent 3 kept full
3. **Agents 4-5** (Critic → PM): Receive full recent context + summarized earlier work

**Verify the fix**:
```bash
# Redeploy orchestrator with updated code
cd deploy
python3 deploy_orchestrator.py --action deploy

# Test full workflow
python3 test_deployed_agents.py --test orchestrator
# Should see all 5 agents complete successfully
```

**Benefits**:
- ✅ Prevents token limit failures in multi-agent workflows
- ✅ Preserves quality (full recent context always available)
- ✅ Scales to 10+ agent workflows
- ✅ Cost efficient (only summarizes when needed)

---

### Issue 3: "Permission denied" or "403 Forbidden"

**Symptom**: Cannot access Cloud Run services

**Solution**: Grant proper IAM permissions

```bash
cd deploy
./fix_iam_permissions.sh
```

Or manually:
```bash
# Get Agent Engine service account
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
SERVICE_ACCOUNT="service-${PROJECT_NUMBER}@gcp-sa-aiplatform-re.iam.gserviceaccount.com"

# Grant Cloud Run Invoker role to all specialist agents
for service in brand-strategist copywriter designer critic project-manager; do
  gcloud run services add-iam-policy-binding ${service}-agent \
    --region=us-central1 \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/run.invoker"
done
```

---

### Issue 4: Notion MCP Not Working

**Symptom**: Project Manager can't create Notion tasks

**Solution**: Verify Notion setup

```bash
# Test Notion database access
cd agents/project_manager
./verify_notion_access.sh
```

**Common Issues:**
- ❌ Database not shared with integration → Share in Notion
- ❌ Wrong database ID → Check URL: `notion.so/workspace/DATABASE_ID?v=...`
- ❌ Wrong environment variable name → Use `NOTION_API_KEY` (not `NOTION_TOKEN`)
- ❌ Tasks database ID not updated → Edit `agents/project_manager/agent.py:59`
- ❌ MCP server version 2.0.0 UUID reformatting bug → **Fixed in latest version** (pins to v1.9.1)

**MCP Version Fix Details:**
The Dockerfile now pins the Notion MCP server to version 1.9.1 to avoid UUID reformatting bugs in version 2.0.0:
```dockerfile
# In agents/project_manager/Dockerfile
RUN npm install -g @notionhq/notion-mcp-server@1.9.1
```

The agent code uses the globally installed version instead of downloading the latest via npx:
```python
# In agents/project_manager/agent.py
server_params = StdioServerParameters(
    command="notion-mcp-server",  # Use globally installed version
    args=[],  # Not: ["npx", "-y", "@notionhq/notion-mcp-server"]
    env=mcp_env
)
```

**How Dynamic Schema Discovery Works:**

The Project Manager now automatically discovers your database schema:
1. Calls `API-retrieve-a-database` to get the schema
2. Extracts exact property names, types, and valid values
3. Uses ONLY the discovered properties (never assumes names)
4. Adapts automatically if you rename or add properties

**Testing Dynamic Schema Discovery:**
```bash
# The agent will work with ANY property names you choose
# Test it by creating a project with your custom database schema
cd deploy
./test_agents.sh pm
```

---

### Issue 5: Docker Build Failures

**Symptom**: `docker build` fails for an agent

**Solution**: Check Docker daemon and dependencies

```bash
# Start Docker daemon
sudo systemctl start docker

# Check Docker is running
docker ps

# Clear Docker cache
docker system prune -af

# Rebuild with no cache
docker build --no-cache -t agent-name .
```

---

### Issue 6: Cloud Run Deployment Timeout

**Symptom**: Deployment takes too long or times out

**Solution**: Increase timeout and memory

```bash
gcloud run deploy agent-name \
  --timeout=300 \
  --memory=1Gi \
  --cpu=1 \
  --region=us-central1
```

---

### Issue 6: Agent Engine Deployment Fails

**Symptom**: `deploy_orchestrator.py` fails

**Solution**: Check specialist URLs are set

```bash
# Verify all URLs in .env
grep AGENT_URL .env

# If missing, deploy specialists first
cd deploy
python3 deploy_all_specialists.py
```

---

## Viewing Logs

### Cloud Run Logs (Specialist Agents)

```bash
# View recent logs for an agent
gcloud run services logs read brand-strategist-agent \
  --region us-central1 \
  --limit 50

# Stream live logs
gcloud run services logs tail brand-strategist-agent \
  --region us-central1
```

### Agent Engine Logs (Creative Director)

```bash
# Fetch logs
cd deploy
./fetch_orchestrator_logs.sh 1h

# Analyze A2A interactions
python3 analyze_agent_logs.py /tmp/orchestrator_logs_*.txt
```

---

## Updating Agents

### Update a Single Specialist Agent

```bash
# Make your changes to the agent code
cd agents/brand_strategist

# Redeploy all specialists (fast, parallel)
cd ../../deploy
python3 deploy_all_specialists.py
```

### Update the Orchestrator

```bash
cd deploy
python3 update_orchestrator.py
```

### Update All Agents

```bash
cd deploy
./deploy_complete_system.sh
```

---

## Cost Estimates

**Typical Monthly Costs** (light usage):

- **Cloud Run** (5 agents):
  - Pay per request
  - Free tier: 2 million requests/month
  - Estimated: $0-10/month

- **Vertex AI Agent Engine** (orchestrator):
  - Pay per request
  - Estimated: $5-20/month

- **Gemini API**:
  - Free tier: 60 requests/minute
  - Paid tier: ~$0.35/1M tokens
  - Estimated: $0-5/month

- **Container Registry**:
  - Storage: ~$0.20/GB/month
  - Estimated: $1-2/month

**Total**: $6-37/month for light usage

**Note**: Enable budget alerts in Google Cloud Console to monitor spending.

---

## Next Steps

After successful deployment:

1. ✅ **Test the system**: Run `./test_agents.sh all`
2. ✅ **Monitor costs**: Set up budget alerts in GCP Console
3. ✅ **Review logs**: Check `./fetch_orchestrator_logs.sh`
4. ✅ **Customize agents**: Modify system instructions in agent files
5. ✅ **Add more agents**: Follow the pattern in existing agents

---

## Additional Resources

- **Revision Workflow Guide**: `docs/REVISION_WORKFLOW.md` - Learn about the automatic quality improvement loop
- **Critic Test Prompts**: `critic_revision_test_prompts.md` - Test scenarios for the revision workflow
- **A2A Inspector Guide**: `tools/a2a-inspector/A2A_INSPECTOR_GUIDE.md`
- **A2A Logging Guide**: `tools/a2a-inspector/A2A_LOGGING_GUIDE.md`
- **Main README**: `README.md`

---

## Key Features

### Critic Revision Workflow

The system includes an intelligent revision workflow that ensures quality:

1. **Critic reviews** all creative work (posts + visuals)
2. **Structured feedback** with scores and Status: `APPROVED` or `NEEDS_REVISION`
3. **Automatic revisions**: Orchestrator calls copywriter/designer with feedback if needed
4. **Maximum 1 revision** per agent to prevent infinite loops
5. **Quality deliverables** reach Project Manager only after approval

See `docs/REVISION_WORKFLOW.md` for complete details and workflow diagrams.

**Test it**: Use prompts from `critic_revision_test_prompts.md` to trigger revision scenarios

---

## Getting Help

**Common Commands:**

```bash
# Check deployment status
gcloud run services list --region=us-central1

# Check Agent Engine deployment
gcloud ai reasoning-engines list --region=us-central1

# View all environment variables
cat .env | grep -v "^#"

# Clean up all resources
cd deploy
./teardown_gcp.sh
```

**Need Help?**
- Review troubleshooting section above
- Check logs for error messages
- Verify all environment variables are set
- Ensure IAM permissions are correct

---

## Summary

**Quick Deployment Steps:**

1. Set up GCP project and enable APIs
2. Get Gemini API key
3. (Optional) Set up Notion databases
4. Configure `.env` file
5. Run `./deploy_complete_system.sh`
7. Test with `./test_agents.sh all`

**That's it!** Your distributed multi-agent system is now deployed and running on Google Cloud.
