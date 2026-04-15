"""
hardware_monitor.py — Freeze detection, timeout wrappers, thread health,
and structured logging for the Raspberry Pi robot dashboard.

Import this module in pageOne.py and dashboard.py.

Quick-start
-----------
from hardware_monitor import (
    timeout_call, safe_db_connect, safe_subprocess_run,
    log_calls, HardwareWatchdog, ThreadHealthMonitor,
    make_watchdog_pet_callback,
    hw_log, thread_log, cycle_log, wd_log,
)
"""

import functools
import logging
import sys
import threading
import time
import traceback

# ─── Named loggers (children of the root "robot" logger) ─────────────────────
# All of these propagate to the root "robot" logger configured in logger_config.py,
# so they automatically pick up whichever handlers are attached there.

hw_log     = logging.getLogger("robot.hardware")   # GPIO / sensor / relay
thread_log = logging.getLogger("robot.thread")     # Thread lifecycle
cycle_log  = logging.getLogger("robot.cycle")      # Cycle step progression
wd_log     = logging.getLogger("robot.watchdog")   # Watchdog / heartbeat


# ─── Timeout wrapper ──────────────────────────────────────────────────────────

def timeout_call(func, timeout: float, default=None, label: str = ""):
    """
    Call func() in a worker thread. If it doesn't return within `timeout`
    seconds, return `default` and log a WARNING.  Never blocks forever.

    Parameters
    ----------
    func    : callable — zero-argument function (use a lambda to pass args)
    timeout : float    — seconds to wait before giving up
    default : any      — value to return on timeout (default None)
    label   : str      — human-readable name shown in log messages

    Raises
    ------
    Re-raises any exception that func() raises (so callers can catch normally).

    Example
    -------
    dist = timeout_call(lambda: sensor.distance, timeout=2.0,
                        default=None, label="sensor.distance")
    """
    name = label or getattr(func, "__qualname__", repr(func))
    result_holder = [default]
    exc_holder    = [None]

    def _worker():
        try:
            result_holder[0] = func()
        except Exception as exc:
            exc_holder[0] = exc

    t = threading.Thread(target=_worker, name=f"timeout_call:{name}", daemon=True)
    t.start()
    t.join(timeout)

    if t.is_alive():
        hw_log.warning(
            "TIMEOUT (%.1fs) waiting for %s — using default %r. "
            "Hardware may be disconnected or blocking.",
            timeout, name, default,
        )
        return default

    if exc_holder[0] is not None:
        raise exc_holder[0]   # propagate so caller can handle it

    return result_holder[0]


# ─── Safe database connection ─────────────────────────────────────────────────

def safe_db_connect(host, user, password, database, connect_timeout: int = 5):
    """
    mysql.connector.connect() with an explicit connect_timeout so it never
    hangs the Kivy event loop. Logs entry and exit at DEBUG level.

    Parameters
    ----------
    connect_timeout : int — seconds before the TCP handshake gives up (default 5)

    Example
    -------
    mydb = safe_db_connect("localhost", "root", "Robot123#", "robotdb")
    """
    import mysql.connector

    hw_log.debug("DB connect → %s/%s (timeout=%ds)", host, database, connect_timeout)
    t0 = time.monotonic()
    try:
        conn = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database,
            connection_timeout=connect_timeout,
        )
        hw_log.debug("DB connect OK %s/%s (%.2fs)", host, database,
                     time.monotonic() - t0)
        return conn
    except Exception:
        hw_log.exception("DB connect FAILED %s/%s after %.2fs",
                         host, database, time.monotonic() - t0)
        raise


# ─── Safe subprocess runner ───────────────────────────────────────────────────

def safe_subprocess_run(cmd, timeout: int = 120, **kwargs):
    """
    subprocess.run() with a hard timeout (default 2 min). Logs start,
    duration, exit code, and any timeout.  Identical call signature to
    subprocess.run() for drop-in replacement.

    Raises subprocess.TimeoutExpired on timeout (same as stdlib).

    Example
    -------
    result = safe_subprocess_run(
        [sys.executable, script_path],
        capture_output=True, text=True
    )
    """
    import subprocess

    label = " ".join(str(c) for c in cmd)
    hw_log.debug("subprocess → %s (timeout=%ds)", label, timeout)
    t0 = time.monotonic()
    try:
        result = subprocess.run(cmd, timeout=timeout, **kwargs)
        hw_log.debug("subprocess ← %s rc=%d (%.1fs)",
                     label, result.returncode, time.monotonic() - t0)
        return result
    except subprocess.TimeoutExpired:
        hw_log.error("subprocess TIMEOUT after %ds: %s", timeout, label)
        raise
    except Exception:
        hw_log.exception("subprocess ERROR: %s", label)
        raise


# ─── Function entry / exit decorator ─────────────────────────────────────────

def log_calls(logger=None):
    """
    Decorator factory: logs entry and exit of the decorated function at DEBUG
    level, including wall-clock time. Re-logs at ERROR on exception.

    Usage
    -----
    @log_calls()                         # uses hw_log
    def my_func(): ...

    @log_calls(logger=cycle_log)         # uses a specific logger
    def my_cycle_func(): ...
    """
    _log = logger or hw_log

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            _log.debug("→ %s()", func.__qualname__)
            t0 = time.monotonic()
            try:
                result = func(*args, **kwargs)
                _log.debug("← %s() [%.3fs]", func.__qualname__,
                            time.monotonic() - t0)
                return result
            except Exception:
                _log.exception("✗ %s() raised after %.3fs",
                                func.__qualname__, time.monotonic() - t0)
                raise
        return wrapper
    return decorator


# ─── Thread health monitor ────────────────────────────────────────────────────

class ThreadHealthMonitor:
    """
    Tracks named threads and periodically logs their alive/dead state.

    Usage
    -----
    monitor = ThreadHealthMonitor(check_interval=30)
    monitor.start()

    # after starting a thread:
    monitor.register(my_thread, "beep_loop")

    # on app shutdown:
    monitor.stop()
    """

    def __init__(self, check_interval: float = 30.0):
        self._threads: dict[str, threading.Thread] = {}
        self._interval = check_interval
        self._stop_event = threading.Event()

    def register(self, thread: threading.Thread, name: str) -> None:
        """Register a thread so the monitor tracks it."""
        self._threads[name] = thread
        thread_log.info("Thread registered: %s (daemon=%s, ident=%s)",
                        name, thread.daemon, thread.ident)

    def start(self) -> None:
        """Start the background health-check loop."""
        t = threading.Thread(
            target=self._run,
            name="ThreadHealthMonitor",
            daemon=True,
        )
        t.start()
        thread_log.info(
            "ThreadHealthMonitor started (check_interval=%.0fs)", self._interval
        )

    def stop(self) -> None:
        """Signal the health-check loop to exit."""
        self._stop_event.set()
        thread_log.info("ThreadHealthMonitor stopped")

    def _run(self) -> None:
        while not self._stop_event.wait(self._interval):
            alive, dead = [], []
            for name, thread in list(self._threads.items()):
                (alive if thread.is_alive() else dead).append(name)
            thread_log.info(
                "Thread health — alive: %s | dead: %s",
                alive or "(none)",
                dead or "(none)",
            )


# ─── Hardware watchdog ────────────────────────────────────────────────────────

class HardwareWatchdog:
    """
    Software watchdog that detects UI/main-thread freezes.

    The Kivy Clock calls pet() via a scheduled callback.  If pet() stops
    being called (because the event loop is blocked), on_freeze() fires.

    Usage
    -----
    wd = HardwareWatchdog(timeout=15)
    wd.start()
    Clock.schedule_interval(make_watchdog_pet_callback(wd), 5)  # pet every 5s
    # on app stop:
    wd.stop()
    """

    def __init__(self, timeout: float = 15.0, on_freeze=None):
        """
        Parameters
        ----------
        timeout    : seconds without a pet() call before firing
        on_freeze  : optional callable(overdue_seconds) — defaults to
                     logging CRITICAL + dumping all thread stacks
        """
        self._timeout    = timeout
        self._last_pet   = time.monotonic()
        self._on_freeze  = on_freeze or self._default_freeze_handler
        self._stop_event = threading.Event()
        self._fired      = False   # prevent repeated firing for same freeze

    def start(self) -> None:
        t = threading.Thread(
            target=self._run, name="HardwareWatchdog", daemon=True
        )
        t.start()
        wd_log.info("Watchdog started (timeout=%.0fs)", self._timeout)

    def stop(self) -> None:
        self._stop_event.set()
        wd_log.info("Watchdog stopped")

    def pet(self) -> None:
        """Reset the watchdog timer. Call this from your Kivy Clock callback."""
        self._last_pet = time.monotonic()
        self._fired    = False

    def _run(self) -> None:
        while not self._stop_event.wait(1.0):
            overdue = time.monotonic() - self._last_pet - self._timeout
            if overdue > 0 and not self._fired:
                self._fired = True
                try:
                    self._on_freeze(overdue)
                except Exception:
                    wd_log.exception("on_freeze handler raised an exception")

    # ------------------------------------------------------------------
    def _default_freeze_handler(self, overdue: float) -> None:
        wd_log.critical(
            "WATCHDOG FIRED — UI has been unresponsive for %.0fs "
            "(expected heartbeat every %.0fs). "
            "Likely cause: blocking call in main/Kivy thread.",
            self._timeout + overdue,
            self._timeout,
        )
        self._dump_all_stacks()

    @staticmethod
    def _dump_all_stacks() -> None:
        """Log the Python call stack of every live thread."""
        frames = sys._current_frames()
        for thread in threading.enumerate():
            frame = frames.get(thread.ident)
            if frame is None:
                continue
            stack = "".join(traceback.format_stack(frame))
            wd_log.critical(
                "Stack for thread %r (id=%s, daemon=%s):\n%s",
                thread.name, thread.ident, thread.daemon, stack,
            )


# ─── Kivy Clock helper ────────────────────────────────────────────────────────

def make_watchdog_pet_callback(watchdog: HardwareWatchdog):
    """
    Return a Kivy Clock-compatible callback that pets the watchdog and
    emits a DEBUG heartbeat log.

    Schedule it at an interval shorter than the watchdog timeout:

        wd = HardwareWatchdog(timeout=15)
        wd.start()
        Clock.schedule_interval(make_watchdog_pet_callback(wd), 5)
    """
    def _pet(dt):
        watchdog.pet()
        wd_log.debug("Heartbeat ♥ (dt=%.3fs)", dt)
    return _pet


# ─── Context manager: timed block ─────────────────────────────────────────────

class timed_block:
    """
    Context manager that logs entry, exit, and elapsed time for any block.
    Logs a WARNING if the block exceeds `warn_threshold` seconds.

    Usage
    -----
    with timed_block("DB write — motion failure", warn_threshold=3.0):
        mydb = safe_db_connect(...)
        mycursor.execute(sql, values)
        mydb.commit()
    """

    def __init__(self, label: str, warn_threshold: float = 2.0,
                 logger=None):
        self._label     = label
        self._threshold = warn_threshold
        self._log       = logger or hw_log
        self._t0: float = 0.0

    def __enter__(self):
        self._t0 = time.monotonic()
        self._log.debug("[ %s ] start", self._label)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = time.monotonic() - self._t0
        if exc_type is not None:
            self._log.error("[ %s ] FAILED after %.2fs: %s",
                            self._label, elapsed, exc_val)
        elif elapsed > self._threshold:
            self._log.warning("[ %s ] SLOW — took %.2fs (threshold %.1fs)",
                              self._label, elapsed, self._threshold)
        else:
            self._log.debug("[ %s ] done (%.2fs)", self._label, elapsed)
        return False   # don't suppress exceptions
