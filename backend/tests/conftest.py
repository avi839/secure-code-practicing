"""
Test configuration. Environment variables are set BEFORE the app is imported so
the settings singleton never sees real keys, the user's .env DEMO_MODE, or the
real database.
"""

import os
import pathlib
import tempfile

_TEST_DB = pathlib.Path(tempfile.gettempdir()) / f"srx_test_{os.getpid()}.db"

os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_TEST_DB.as_posix()}"
os.environ["OPENAI_API_KEY"] = ""
os.environ["ANTHROPIC_API_KEY"] = ""
os.environ["GOOGLE_API_KEY"] = ""
os.environ["DEMO_MODE"] = "false"
os.environ["DEMO_LATENCY_MS"] = "0"
os.environ["ENVIRONMENT"] = "test"


def pytest_sessionfinish(session, exitstatus):
    for suffix in ("", "-wal", "-shm", "-journal"):
        try:
            pathlib.Path(str(_TEST_DB) + suffix).unlink()
        except OSError:
            pass
