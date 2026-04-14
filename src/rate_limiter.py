import time
import threading
from collections import deque
from src.config import ConfigLoader

class RateLimiter:
    def __init__(self, max_requests_per_minute: int = 30):
        config = ConfigLoader()
        self.enabled = bool(config.get('rate_limiting.enabled', False))
        if self.enabled:
            max_requests_per_minute = int(config.get('rate_limiting.max_requests_per_minute', 30))
        
        self.max_requests_per_minute = max_requests_per_minute
        self.wait_on_limit = bool(config.get('rate_limiting.wait_on_limit', True)) if self.enabled else False
        self.requests = deque()
        self.lock = threading.Lock()
    
    def acquire(self, wait: bool = True) -> bool:
        if not self.enabled:
            return True
        while True:
            wait_time = 0.0
            with self.lock:
                now = time.time()

                # Remove requests older than 1 minute
                cutoff = now - 60
                while self.requests and self.requests[0] < cutoff:
                    self.requests.popleft()

                if len(self.requests) < self.max_requests_per_minute:
                    self.requests.append(now)
                    return True

                if not wait or not self.wait_on_limit:
                    return False

                # Calculate wait time and retry in loop
                oldest_request = self.requests[0]
                wait_time = max(0.0, oldest_request + 60 - now)
                print(f"[RateLimiter] Rate limit reached. Waiting {wait_time:.2f}s before next request...")

            # Release lock before sleeping to avoid deadlock
            if wait_time > 0:
                time.sleep(wait_time)

global_llm_rate_limiter = RateLimiter()
