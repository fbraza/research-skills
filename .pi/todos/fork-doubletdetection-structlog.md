---
title: "Fork doubletdetection to fix tqdm progress bar and make it structlog-compatible"
status: open
tags: [enhancement, upstream-fix, logging, doublet-detection]
created: 2026-04-07
---

## Problem

`doubletdetection.BoostClassifier` hardcodes `tqdm` at line 192 of `doubletdetection.py`:

```python
for i in tqdm(range(self.n_iters)):
```

This produces ~100 lines of noisy output per sample (tqdm bars, scanpy PCA/neighbors/clustering logs, FutureWarnings, UserWarnings) that cannot be suppressed or reformatted from the outside.

### Root cause
- tqdm writes directly to stderr, bypassing Python `logging` entirely
- scanpy's internal logging (PCA, neighbors, clustering) is emitted via stdlib logging at verbosity >= 3
- doubletdetection has a `verbose` param but it only controls its own `print()` statements, NOT the scanpy/tqdm noise
- The `_DevNull` stderr redirect approach in `src/logging_config.py` crashes tqdm's multiprocessing lock on some platforms

### Fork changes needed
1. **Replace `tqdm` with an optional callback** — accept a `progress_callback: Callable[[int, int], None]` parameter (signature: `progress_callback(current_iter, total_iters)`) so callers can emit structlog messages or any custom progress
2. **Add `scanpy_verbosity` parameter** — let the caller control scanpy's verbosity level internally (default: 0 for silent)
3. **Suppress warnings internally** — catch `FutureWarning` and `UserWarning` within the library itself (the "Use `scanpy.tl.leiden` instead" and "pkg_resources is deprecated" warnings are noise the library should handle)
4. **Remove `verbose` print() calls** — replace with Python `logging` so structlog can capture them through the stdlib integration

### Current workaround
The `suppress_scanpy()` context manager in `src/logging_config.py` works on macOS/Linux but the stderr redirect (`sys.stderr = _DevNull()`) breaks tqdm's multiprocessing semaphore. The safest workaround until the fork is done:

```python
# Option A: disable tqdm globally before importing doubletdetection
import tqdm
original_tqdm = tqdm.tqdm
tqdm.tqdm = lambda *a, **kw: iter(a[0]) if a else iter([])

# Option B: monkeypatch doubletdetection after import
import doubletdetection
import types
original_fit = doubletdetection.BoostClassifier.fit
# wrap with scanpy verbosity=0 + warnings suppression
```

### Reference
- Original issue analysis: structlog research session (2026-04-07)
- structlog stdlib integration: https://www.structlog.org/en/stable/standard-library.html
- doubletdetection source: `.venv/lib/python3.13/site-packages/doubletdetection/doubletdetection.py`
- `src/logging_config.py` — the structlog setup (already written, partially functional)
