"""
Shared progress tracking, ETA formatting, and error circuit breaker.
Used by filter.py and websearch_gate.py for consistent UX.

Output philosophy: QUIET by default (summary only). Use --verbose for per-item detail.
Terminal users shouldn't have to scroll through hundreds of lines.
"""

import signal
import sys
import time


def format_eta(seconds: float) -> str:
    """Format seconds into human-readable ETA string."""
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        return f"{int(seconds // 60)}m {int(seconds % 60)}s"
    else:
        return f"{int(seconds // 3600)}h {int(seconds % 3600 // 60)}m"


class InterruptHandler:
    """Graceful SIGINT/SIGTERM handler. Check `handler.interrupted` in loops."""

    def __init__(self):
        self.interrupted = False
        signal.signal(signal.SIGINT, self._handle)
        signal.signal(signal.SIGTERM, self._handle)

    def _handle(self, signum, frame):
        self.interrupted = True
        print("\n⚠️  Interrupted! Writing partial results...", file=sys.stderr)


class ProgressTracker:
    """Track progress through a list of items with ETA and error counting.

    Default (verbose=False): single updating line via \\r, no scroll.
    Verbose (verbose=True): one line per item (for debugging/agents).

    Usage:
        tracker = ProgressTracker(total=100, verbose=False)
        for item in items:
            if tracker.should_stop():
                break
            tracker.tick(f"{item}: OK")
        tracker.finish_line()  # clear the \\r line
    """

    def __init__(
        self,
        total: int,
        already_done: int = 0,
        max_errors: int = 10,
        interrupt: InterruptHandler | None = None,
        verbose: bool = False,
    ):
        self.total = total
        self.done = already_done
        self.initial_done = already_done
        self.errors = 0
        self.max_errors = max_errors
        self.start_time = time.time()
        self.interrupt = interrupt or InterruptHandler()
        self.verbose = verbose

    def should_stop(self) -> bool:
        """Check if processing should stop (interrupt or too many errors)."""
        return self.interrupt.interrupted or self.errors >= self.max_errors

    def tick(self, message: str = "") -> None:
        """Record one completed item and print progress."""
        self.done += 1
        elapsed = time.time() - self.start_time
        processed = self.done - self.initial_done
        rate = processed / max(elapsed, 0.1)
        remaining = (self.total - self.done) / max(rate, 0.001)
        eta_str = format_eta(remaining)

        if self.verbose:
            print(f"  [{self.done}/{self.total}] {message} | ETA: {eta_str}", file=sys.stderr)
        else:
            # Single updating line — no scroll
            pct = int(self.done / self.total * 100) if self.total else 100
            print(f"\r  [{self.done}/{self.total}] {pct}% | ETA: {eta_str}   ", end="", file=sys.stderr)

    def record_error(self, message: str = "") -> bool:
        """Record an error. Returns False if max errors reached (caller should stop)."""
        self.errors += 1
        if self.verbose:
            print(f"  ⚠️  [{self.done + 1}/{self.total}] {message}", file=sys.stderr)
        if self.errors >= self.max_errors:
            self.finish_line()
            print(f"❌ Too many errors ({self.errors}). Stopping.", file=sys.stderr)
            print("   This usually means an API is rate-limiting or unreachable.", file=sys.stderr)
            print("   Try again later or increase --delay.", file=sys.stderr)
            return False
        return True

    def finish_line(self) -> None:
        """Clear the \\r progress line (call before printing summary)."""
        if not self.verbose:
            print("", file=sys.stderr)  # newline after \r line

    @property
    def was_interrupted(self) -> bool:
        return self.interrupt.interrupted

    @property
    def hit_error_limit(self) -> bool:
        return self.errors >= self.max_errors
