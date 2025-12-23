import os

import dspy

from braintrust.wrappers.dspy import BraintrustDSpyCallback
from dotenv import load_dotenv


load_dotenv()

lm = dspy.LM(model='gpt-4o-mini', api_key=os.getenv('OPENAI_API_KEY'))
dspy.configure(lm=lm, callbacks=[BraintrustDSpyCallback()])


class AgentSignature(dspy.Signature):
    """You are a helpful assistant that can answer any question."""

    question: str = dspy.InputField(description='The question to answer')
    ctx: list[dict] = dspy.InputField(
        description='The context to use for the question'
    )
    answer: str = dspy.OutputField(description='The answer to the question')
    completed_task: bool = dspy.OutputField(
        description='Whether the task is complete or need more input'
    )


agent = dspy.ChainOfThought(signature=AgentSignature)
