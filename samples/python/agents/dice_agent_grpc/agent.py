import random

from collections.abc import AsyncIterable

from google.adk import Runner
from google.adk.agents import LlmAgent
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.sessions import InMemorySessionService
from google.genai import types


def roll_dice(N: int = 6) -> int:
    """Rolls an N sided dice. If number of sides aren't given, uses 6.

    Args:
      N: the number of the side of the dice to roll.

    Returns:
      A number between 1 and N, inclusive
    """
    return random.randint(1, N)


def check_prime(nums: list[int]) -> str:
    """Check if a given list of numbers are prime.

    Args:
      nums: The list of numbers to check.

    Returns:
      A str indicating which number is prime.
    """
    primes = set()
    for number in nums:
        number = int(number)
        if number <= 1:
            continue
        is_prime = True
        for i in range(2, int(number**0.5) + 1):
            if number % i == 0:
                is_prime = False
            break
        if is_prime:
            primes.add(number)
    return (
        'No prime numbers found.'
        if not primes
        else f'{", ".join(str(num) for num in primes)} are prime numbers.'
    )


def create_agent() -> LlmAgent:
    return LlmAgent(
        model='gemini-2.0-flash-001',
        name='dice_roll_agent',
        instruction="""
You roll dice and answer questions about the outcome of the dice rolls.
You can roll dice of different sizes.
You can use multiple tools in parallel by calling functions in parallel (in one request and in one round).
The only things you do are roll dice for the user and discuss the outcomes.
It is ok to discuss previous dice roles, and comment on the dice rolls.
When you are asked to roll a die, you must call the roll_die tool with the number of sides. Be sure to pass in an integer. Do not pass in a string.
You should never roll a die on your own.
When checking prime numbers, call the check_prime tool with a list of integers. Be sure to pass in a list of integers. You should never pass in a string.
You should not check prime numbers before calling the tool.
When you are asked to roll a die and check prime numbers, you should always make the following two function calls:
1. You should first call the roll_die tool to get a roll. Wait for the function response before calling the check_prime tool.
2. After you get the function response from roll_die tool, you should call the check_prime tool with the roll_die result.
    2.1 If user asks you to check primes based on previous rolls, make sure you include the previous rolls in the list.
3. When you respond, you must include the roll_die result from step 1.
You should always perform the previous 3 steps when asking for a roll and checking prime numbers.
You should not rely on the previous history on prime results.
    """,
        description='Rolls an N-sided dice and answers questions about the outcome of the dice rolls. Can also answer questions about prime numbers.',
        tools=[
            roll_dice,
            check_prime,
        ],
    )


class DiceAgent:
    """An agent that handles reimbursement requests."""

    SUPPORTED_CONTENT_TYPES = ['text', 'text/plain']

    def __init__(self):
        self._agent = create_agent()
        self._user_id = 'remote_agent'
        self._runner = Runner(
            app_name=self._agent.name,
            agent=self._agent,
            artifact_service=InMemoryArtifactService(),
            session_service=InMemorySessionService(),
            memory_service=InMemoryMemoryService(),
        )

    async def stream(
        self, query, session_id
    ) -> AsyncIterable[tuple[bool, str]]:
        session = await self._runner.session_service.get_session(
            app_name=self._agent.name,
            user_id=self._user_id,
            session_id=session_id,
        )
        content = types.Content(
            role='user', parts=[types.Part.from_text(text=query)]
        )
        if session is None:
            session = await self._runner.session_service.create_session(
                app_name=self._agent.name,
                user_id=self._user_id,
                state={},
                session_id=session_id,
            )
        async for event in self._runner.run_async(
            user_id=self._user_id, session_id=session.id, new_message=content
        ):
            if event.is_final_response():
                yield (
                    True,
                    '\n'.join([p.text for p in event.content.parts if p.text]),
                )
            else:
                yield (False, 'working...')
