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

"""A2A Logging Plugin - LOCAL TESTING ONLY.

IMPORTANT: This plugin CANNOT be deployed to Agent Engine.
   - Cloudpickle creates module dependencies that can't be resolved in Agent Engine.
   - Custom plugins defined in agent code cause ModuleNotFoundError.
   - Only ADK's built-in plugins (like LoggingPlugin) work with deployment.

Usage:
   - Use this for LOCAL testing only by adding to agent.py plugins list.
   - For production: View A2A calls via Cloud Logging or add logging to Cloud Run agents.

How to use locally:
   In agent.py, uncomment these lines::

       from .a2a_logging_plugin import A2ALoggingPlugin

       plugins = [LoggingPlugin(), A2ALoggingPlugin(name='a2a_logger')]

   Then run locally with: python agents/creative_director/agent.py
"""

import datetime
import json
import logging

from google.adk.plugins.base_plugin import BasePlugin


# Configure logging
logger = logging.getLogger('ai_creative_studio.a2a_logging')
logger.setLevel(logging.INFO)


class A2ALoggingPlugin(BasePlugin):
    """Plugin to log A2A communication between orchestrator and specialist agents.

    Uses after_tool_callback pattern from Agentverse Architect codelab (Step 7).
    This callback intercepts tool execution results to log A2A calls.
    """

    def after_tool_callback(self, tool_context):  # noqa: ANN001, ANN201
        """Intercept tool execution to log A2A communication.

        This callback runs after each tool call completes, capturing:
        - Which specialist agent was called
        - What request was sent (tool arguments)
        - What response was received (tool result)
        """
        tool_name = tool_context.tool_name

        # Only log AgentTool calls to our specialist agents
        # Skip if this is some other tool type
        specialist_agents = [
            'brand_strategist',
            'copywriter',
            'designer',
            'critic',
            'project_manager',
        ]
        if tool_name not in specialist_agents:
            return

        # Log the A2A communication
        logger.info('=' * 70)
        logger.info('🔗 A2A CALL TO: %s', tool_name.upper())
        logger.info('=' * 70)

        # Log timestamp
        timestamp = datetime.datetime.now(tz=datetime.timezone.utc).strftime(
            '%Y-%m-%d %H:%M:%S'
        )
        logger.info('Timestamp: %s', timestamp)

        # Log input (request sent to specialist agent)
        if hasattr(tool_context, 'arguments') and tool_context.arguments:
            logger.info('\n📤 REQUEST TO %s:', tool_name)
            try:
                logger.info(json.dumps(tool_context.arguments, indent=2))
            except Exception:  # noqa: BLE001
                logger.info(str(tool_context.arguments))

        # Log output (response received from specialist agent)
        if hasattr(tool_context, 'result') and tool_context.result:
            logger.info('\n📥 RESPONSE FROM %s:', tool_name)
            result_str = str(tool_context.result)
            # Truncate very long responses for readability
            if len(result_str) > 2000:  # noqa: PLR2004
                truncated = (
                    result_str[:2000]
                    + '\n... (truncated, full length: %d chars)'
                )
                logger.info(truncated, len(result_str))
            else:
                logger.info(result_str)

        # Log any errors
        if hasattr(tool_context, 'error') and tool_context.error:
            logger.error('\n❌ ERROR IN %s:', tool_name)
            logger.error(str(tool_context.error))

        logger.info('%s\n', '=' * 70)
