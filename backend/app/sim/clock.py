"""
Simulated Clock for Trust Analyst.
Single source of simulated time across the entire application.
"""

import threading

# Default simulation baseline epoch: Nov 15, 2023 00:00:00 UTC
DEFAULT_START_TIME = 1700000000


class SimulatedClock:
    """Thread-safe simulated clock."""

    def __init__(self, initial_time: int = DEFAULT_START_TIME):
        self._current_time = initial_time
        self._lock = threading.Lock()

    def now(self) -> int:
        """Returns current simulated epoch time in seconds."""
        with self._lock:
            return self._current_time

    def advance(self, seconds: int) -> int:
        """Advances the simulated clock by seconds and returns the new time."""
        if seconds < 0:
            raise ValueError("Cannot rewind simulated time")
        with self._lock:
            self._current_time += seconds
            return self._current_time

    def set_time(self, epoch: int) -> int:
        """Explicitly sets simulated time to an epoch timestamp."""
        with self._lock:
            self._current_time = epoch
            return self._current_time

    def reset(self, initial_time: int = DEFAULT_START_TIME) -> int:
        """Resets clock to initial baseline."""
        with self._lock:
            self._current_time = initial_time
            return self._current_time

    def iso_string(self) -> str:
        """Returns ISO formatted string of current simulated time."""
        from datetime import datetime, timezone

        return datetime.fromtimestamp(self.now(), tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


_clock_instance: SimulatedClock | None = None


def get_clock() -> SimulatedClock:
    """Returns singleton SimulatedClock instance."""
    global _clock_instance
    if _clock_instance is None:
        _clock_instance = SimulatedClock()
    return _clock_instance
