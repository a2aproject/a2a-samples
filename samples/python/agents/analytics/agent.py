import base64
import logging

from collections.abc import AsyncIterable
from io import BytesIO
from typing import Any
from uuid import uuid4

import matplotlib.pyplot as plt
import pandas as pd

from crewai import Agent, Crew, Task
from crewai.process import Process
from crewai.tools import tool
from dotenv import load_dotenv
from pydantic import BaseModel
from utils import cache


load_dotenv()

logger = logging.getLogger(__name__)


class Imagedata(BaseModel):
    id: str | None = None
    name: str | None = None
    mime_type: str | None = None
    bytes: str | None = None
    error: str | None = None


@tool('ChartGenerationTool')
def generate_chart_tool(prompt: str, session_id: str) -> str:
    """Generates a bar chart image from CSV-like input using matplotlib."""
    logger.info(f'>>>Chart tool called with prompt: {prompt}')

    if not prompt:
        raise ValueError('Prompt cannot be empty')

    try:
        # Parse CSV-like input
        from io import StringIO

        df = pd.read_csv(StringIO(prompt))
        if df.shape[1] != 2:
            raise ValueError(
                'Input must have exactly two columns: Category and Value'
            )
        df.columns = ['Category', 'Value']
        df['Value'] = pd.to_numeric(df['Value'], errors='coerce')
        if df['Value'].isnull().any():
            raise ValueError('All values must be numeric')

        # Generate bar chart
        fig, ax = plt.subplots()
        ax.bar(df['Category'], df['Value'])
        ax.set_xlabel('Category')
        ax.set_ylabel('Value')
        ax.set_title('Bar Chart')

        # Save to buffer
        buf = BytesIO()
        plt.savefig(buf, format='png')
        plt.close(fig)
        buf.seek(0)
        image_bytes = buf.read()

        # Encode image
        data = Imagedata(
            bytes=base64.b64encode(image_bytes).decode('utf-8'),
            mime_type='image/png',
            name='generated_chart.png',
            id=uuid4().hex,
        )

        logger.info(
            f'Caching image with ID: {data.id} for session: {session_id}'
        )

        # Cache image
        session_data = cache.get(session_id) or {}
        session_data[data.id] = data
        cache.set(session_id, session_data)

        return data.id

    except Exception as e:
        logger.error(f'Error generating chart: {e}')
        return -999999999


class ChartGenerationAgent:
    SUPPORTED_CONTENT_TYPES = ['text', 'text/plain', 'image/png']

    def __init__(self):
        self.chart_creator_agent = Agent(
            role='Chart Creation Expert',
            goal='Generate a bar chart image based on structured CSV input.',
            backstory='You are a data visualization expert who transforms structured data into visual charts.',
            verbose=False,
            allow_delegation=False,
            tools=[generate_chart_tool],
        )

        self.chart_creation_task = Task(
            description=(
                "You are given a prompt: '{user_prompt}'.\n"
                "If the prompt includes comma-separated key:value pairs (e.g. 'a:100, b:200'), "
                "reformat it into CSV with header 'Category,Value'.\n"
                "Ensure it becomes two-column CSV, then pass that to the 'ChartGenerationTool'.\n"
                "Use session ID: '{session_id}' when calling the tool."
            ),
            expected_output='The id of the generated chart image',
            agent=self.chart_creator_agent,
        )

        self.chart_crew = Crew(
            agents=[self.chart_creator_agent],
            tasks=[self.chart_creation_task],
            process=Process.sequential,
            verbose=False,
        )

    import uuid

    def invoke(self, query, session_id: str | None = None) -> str:
        # Normalize or generate session_id
        session_id = session_id or f'session-{uuid.uuid4().hex}'
        logger.info(
            f'[invoke] Using session_id: {session_id} for query: {query}'
        )

        inputs = {
            'user_prompt': query,
            'session_id': session_id,
        }

        response = self.chart_crew.kickoff(inputs)
        logger.info(f'[invoke] Chart tool returned image ID: {response}')
        return response

    async def stream(self, query: str) -> AsyncIterable[dict[str, Any]]:
        raise NotImplementedError('Streaming is not supported.')

    def get_image_data(self, session_id: str, image_key: str) -> Imagedata:
        session_data = cache.get(session_id)

        if not session_data:
            logger.error(
                f'[get_image_data] No session data for session_id: {session_id}'
            )
            return Imagedata(
                error=f'No session data found for session_id: {session_id}'
            )

        if image_key not in session_data:
            logger.error(
                f'[get_image_data] Image key {image_key} not found in session data'
            )
            return Imagedata(
                error=f'Image ID {image_key} not found in session {session_id}'
            )

        return session_data[image_key]
