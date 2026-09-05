import sys
sys.path.insert(0, r'X:\second-brain-kb')
from brain_agent_v4 import run_multi_agent
import asyncio

async def test():
    await run_multi_agent('Create a simple test file test_hello.py with a function that returns Hello, World! and run it')

asyncio.run(test())