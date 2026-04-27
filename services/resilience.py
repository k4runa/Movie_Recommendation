import asyncio
import random
import logging
import time
from functools import wraps
from typing import Callable, Type, Tuple, Optional

logger = logging.getLogger(__name__)

class CircuitBreakerOpen(Exception):
    """Raised when the circuit breaker is open."""
    pass

class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 30.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "CLOSED" # CLOSED, OPEN, HALF_OPEN

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logger.error(f"Circuit breaker opened due to {self.failure_count} failures")

    def record_success(self):
        self.failure_count = 0
        self.state = "CLOSED"

    def can_execute(self) -> bool:
        if self.state == "CLOSED":
            return True
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
                return True
            return False
        if self.state == "HALF_OPEN":
            return True
        return False

def resilient_call(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 10.0,
    retry_on: Tuple[Type[Exception], ...] = (Exception,),
    circuit_breaker: Optional[CircuitBreaker] = None
):
    """
    Decorator for async functions that adds:
    1. Exponential backoff with jitter
    2. Circuit Breaker support (optional)
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if circuit_breaker and not circuit_breaker.can_execute():
                logger.warning(f"Circuit breaker is OPEN for {func.__name__}. Skipping call.")
                raise CircuitBreakerOpen(f"Circuit for {func.__name__} is currently open")

            delay = base_delay
            for attempt in range(max_retries):
                try:
                    result = await func(*args, **kwargs)
                    if circuit_breaker:
                        circuit_breaker.record_success()
                    return result
                except retry_on as e:
                    if attempt == max_retries - 1:
                        if circuit_breaker:
                            circuit_breaker.record_failure()
                        logger.error(f"{func.__name__} failed after {max_retries} attempts: {e}")
                        raise e
                    
                    sleep_time = min(delay * (2 ** attempt) + random.uniform(0, 0.5), max_delay)
                    logger.warning(f"{func.__name__} attempt {attempt + 1} failed: {e}. Retrying in {sleep_time:.2f}s...")
                    await asyncio.sleep(sleep_time)
            
            return None
        return wrapper
    return decorator
