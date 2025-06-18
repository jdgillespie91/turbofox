import secrets
import shutil
import socket
import sys
import time
from collections.abc import Callable

from invoke.context import Context
from invoke.tasks import task


def _generate_id() -> str:
    """Generates a 7-character random hexadecimal string."""
    return secrets.token_hex(4)[:7]


class Result:
    def __init__(self, ok: bool, stdout: str | None = None, stderr: str | None = None):
        self.ok = ok
        self.stdout = stdout
        self.stderr = stderr


def _run_command(
    c: Context,
    command: str | Callable[[], None],
    on_start: Callable[[], None],
    on_success: Callable[[], None],
    on_failure: Callable[[], None],
):
    on_start()

    start_time = time.perf_counter()

    if isinstance(command, str):
        result = c.run(command, pty=True, hide=True, warn=False)  # type: ignore
        result = Result(ok=result.ok, stdout=result.stdout, stderr=result.stderr)  # type: ignore
    else:
        try:
            command()
            result = Result(ok=True)
        except Exception as e:
            result = Result(ok=False, stderr=str(e))

    end_time = time.perf_counter()
    duration_ms = int((end_time - start_time) * 1000)

    if result.ok:
        on_success()
        if duration_ms > 10_000:
            print(f"\033[90mTook {duration_ms / 1000:.2f}s\033[0m")
        else:
            print(f"\033[90mTook {duration_ms}ms\033[0m")
    else:
        on_failure()
        if duration_ms > 10_000:
            print(f"\033[90mTook {duration_ms / 1000:.2f}s\033[0m")
        else:
            print(f"\033[90mTook {duration_ms}ms\033[0m")

        print()
        terminal_width = shutil.get_terminal_size().columns
        print("─" * terminal_width)
        print()

        if result.stderr:
            print(result.stderr)
        if result.stdout:
            print(result.stdout)

        sys.exit(1)


def _is_port_in_use(port: int) -> bool:
    """Check if a port is in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("localhost", port)) == 0


@task
def dev(c: Context):
    # Check if the app is already running
    if _is_port_in_use(8000):
        print("🔴 The app is already running on port 8000. Please stop it first.")
        sys.exit(1)

    # Purge the database.
    c.run("rm -f data/transactions.db", pty=True)  # type: ignore
    c.run("rm -f data/transactions.db-shm", pty=True)  # type: ignore
    c.run("rm -f data/transactions.db-wal", pty=True)  # type: ignore

    # Configure the environment.
    env = {
        "LOGFIRE_CONSOLE": "false",
    }

    # Run the app.
    c.run("uv run uvicorn app.app:app --reload", env=env, pty=True)  # type: ignore


@task
def format(c: Context):
    _run_command(
        c,
        "uv run ruff format",
        lambda: print(f"⏳ Formatting...", end="\r"),
        lambda: print(f"🟢 Formatting complete"),
        lambda: print(f"🔴 Formatting failed"),
    )


@task
def lint(c: Context):
    _run_command(
        c,
        "uv run ruff check",
        lambda: print(f"⏳ Linting...", end="\r"),
        lambda: print(f"🟢 Linting complete"),
        lambda: print(f"🔴 Linting failed"),
    )


@task
def typecheck(c: Context):
    _run_command(
        c,
        "uv run pyright",
        lambda: print(f"⏳ Type-checking...", end="\r"),
        lambda: print(f"🟢 Type-checking complete"),
        lambda: print(f"🔴 Type-checking failed"),
    )


@task
def test(c: Context):
    # Configure the environment.
    env = {
        "LOGFIRE_CONSOLE": "false",
        "SQLITE_DATABASE": f"/tmp/transactions-{_generate_id()}.db",
    }

    _run_command(
        c,
        lambda: c.run("uv run pytest", env=env, pty=False, hide=True, warn=False),  # type: ignore
        lambda: print(f"⏳ Tests running...", end="\r"),
        lambda: print(f"🟢 Tests complete"),
        lambda: print(f"🔴 Tests failed"),
    )


@task
def all(c: Context):
    tasks = [format, lint, typecheck, test]
    for i, task in enumerate(tasks):
        task(c)
        if i < len(tasks) - 1:
            print()
