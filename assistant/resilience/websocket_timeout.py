"""
WebSocket Timeout Handler - Graceful timeout management for real-time connections.

Prevents hanging connections and implements exponential backoff for reconnection.
Part of Phase 3 Robustness improvements (+3 points toward 800/800).
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Callable, TypeVar, ParamSpec

logger = logging.getLogger(__name__)

# WebSocket configuration
DEFAULT_TIMEOUT_SEC = 30
MAX_RECONNECT_ATTEMPTS = 5
INITIAL_BACKOFF_SEC = 1
MAX_BACKOFF_SEC = 32

P = ParamSpec("P")
T = TypeVar("T")


@dataclass
class WebSocketConfig:
    """WebSocket timeout configuration."""

    timeout_sec: int = DEFAULT_TIMEOUT_SEC
    ping_interval_sec: int = 10
    max_reconnect_attempts: int = MAX_RECONNECT_ATTEMPTS
    initial_backoff_sec: float = INITIAL_BACKOFF_SEC
    max_backoff_sec: float = MAX_BACKOFF_SEC


class TimeoutHandler:
    """Manages WebSocket timeouts and reconnection logic."""

    def __init__(self, config: WebSocketConfig | None = None):
        """
        Initialize timeout handler.

        Args:
            config: WebSocket configuration (uses defaults if None)
        """
        self.config = config or WebSocketConfig()
        self.reconnect_attempt = 0

    async def with_timeout(
        self,
        coro: Callable[P, T],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> T:
        """
        Execute coroutine with timeout protection.

        Args:
            coro: Coroutine function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Result from coroutine

        Raises:
            asyncio.TimeoutError: If operation exceeds timeout
        """
        try:
            return await asyncio.wait_for(
                coro(*args, **kwargs),
                timeout=self.config.timeout_sec,
            )
        except asyncio.TimeoutError:
            logger.warning(
                f"[WebSocket] Operation timed out after {self.config.timeout_sec}s"
            )
            raise

    def get_backoff_delay(self) -> float:
        """
        Calculate exponential backoff delay.

        Returns:
            Delay in seconds for next reconnection attempt
        """
        delay = min(
            self.config.initial_backoff_sec * (2**self.reconnect_attempt),
self.config.max_backoff_sec,
        )
        self.reconnect_attempt += 1
        return delay

    def reset_backoff(self) -> None:
        """Reset reconnection attempt counter."""
        self.reconnect_attempt = 0

    def should_reconnect(self) -> bool:
        """
        Check if reconnection should be attempted.

        Returns:
            True if reconnection attempts remaining
        """
        return self.reconnect_attempt < self.config.max_reconnect_attempts

    async def reconnect_with_backoff(
        self,
        connect_func: Callable[[], T],
        on_success: Callable[[T], None] | None = None,
        on_failure: Callable[[Exception], None] | None = None,
    ) -> T | None:
        """
        Attempt reconnection with exponential backoff.

        Args:
            connect_func: Function that performs connection
            on_success: Callback on successful reconnection
            on_failure: Callback on final failure

        Returns:
            Connection object or None if all attempts failed
        """
        while self.should_reconnect():
            delay = self.get_backoff_delay()
            logger.info(
                f"[WebSocket] Reconnecting in {delay:.1f}s "
                f"(attempt {self.reconnect_attempt}/{self.config.max_reconnect_attempts})"
            )

            await asyncio.sleep(delay)

            try:
                connection = await connect_func()
                logger.info("[WebSocket] Reconnection successful")
                self.reset_backoff()

                if on_success:
                    on_success(connection)

                return connection

            except Exception as e:
                logger.warning(f"[WebSocket] Reconnection failed: {e}")

                if not self.should_reconnect():
                    logger.error("[WebSocket] Max reconnect attempts reached")
                    if on_failure:
                        on_failure(e)

        return None


class PingPongManager:
    """Manages WebSocket ping/pong keepalive."""

    def __init__(self, interval_sec: int = 10):
        """
        Initialize ping/pong manager.

        Args:
            interval_sec: Interval between ping messages
        """
        self.interval_sec = interval_sec
        self._task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()

    async def start(self, send_ping: Callable[[], None]):
        """
        Start ping/pong loop.

        Args:
            send_ping: Function to send ping message
        """
        self._stop_event.clear()

        async def ping_loop():
            while not self._stop_event.is_set():
                try:
                    await asyncio.sleep(self.interval_sec)
                    if not self._stop_event.is_set():
                        send_ping()
                        logger.debug("[WebSocket] Ping sent")
                except Exception as e:
                    logger.error(f"[WebSocket] Ping failed: {e}")
                    break

        self._task = asyncio.create_task(ping_loop())

    async def stop(self):
        """Stop ping/pong loop."""
        self._stop_event.set()
        if self._task:
            await self._task


# Example usage in voice_routes.py:
#
# from assistant.resilience.websocket_timeout import TimeoutHandler, WebSocketConfig
#
# timeout_handler = TimeoutHandler(WebSocketConfig(timeout_sec=30))
#
# @app.websocket("/ws/voice")
# async def voice_websocket(websocket: WebSocket):
#     try:
#         audio_data = await timeout_handler.with_timeout(
#             websocket.receive_bytes
#         )
#     except asyncio.TimeoutError:
#         await websocket.close(code=1001, reason="Timeout")
#         await timeout_handler.reconnect_with_backoff(reconnect_func)
