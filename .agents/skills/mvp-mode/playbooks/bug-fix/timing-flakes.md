# Timing flakes: condition-based waiting

Load at bug-fix step 3 when the confirmed cause is a timing flake.

A test that sleeps a guessed duration passes on fast machines and fails under
load. Wait for the condition you actually care about:

```python
# before — guessing at timing
time.sleep(0.5)
assert job.state == "done"

# after — waiting for the condition
wait_for(lambda: job.state == "done", "job completed")
assert job.result == expected
```

A sufficient helper (async variant: `await asyncio.sleep(interval)`):

```python
import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")

def wait_for(
    condition: Callable[[], T | None],
    description: str,
    timeout: float = 5.0,
    interval: float = 0.01,
) -> T:
    """Poll until condition() returns a truthy value; fail loudly on timeout."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = condition()
        if result:
            return result
        time.sleep(interval)
    raise TimeoutError(f"timed out after {timeout}s waiting for {description}")
```

Common mistakes: polling with no timeout (hangs forever); evaluating state
captured before the loop instead of calling the getter inside it; polling so
tightly it starves the condition.

A fixed sleep is legitimate only when testing real timed behavior (debounce,
tick intervals): first wait for the triggering condition, then sleep a
duration derived from the known timing, with a comment saying why.
