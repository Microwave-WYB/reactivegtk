import asyncio
import threading


def start_event_loop() -> tuple[asyncio.AbstractEventLoop, threading.Thread]:
    """Start the asyncio event loop in a separate thread."""
    event_loop = asyncio.new_event_loop()
    thread = threading.Thread(target=event_loop.run_forever, daemon=True)
    thread.start()
    return event_loop, thread
