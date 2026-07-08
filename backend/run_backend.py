"""Local FastAPI runner with a psycopg-compatible Windows event loop."""

import asyncio
import sys

import uvicorn

from app.config.settings import settings


def main() -> None:
    config = uvicorn.Config(
        "app.main:app",
        host="127.0.0.1",
        port=settings.PORT,
        loop="asyncio",
        log_level="info",
    )
    server = uvicorn.Server(config)

    if sys.platform == "win32":
        loop = asyncio.SelectorEventLoop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(server.serve())
        finally:
            loop.close()
    else:
        asyncio.run(server.serve())


if __name__ == "__main__":
    main()