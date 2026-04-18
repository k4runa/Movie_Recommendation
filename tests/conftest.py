import pytest
import asyncio

@pytest.fixture(scope="session")
def event_loop():
    """
    Force all async tests to use the exact same event loop.
    This prevents SQLAlchemy's global connection pool from being attached
    to a closed loop when running multiple test files consecutively.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()
