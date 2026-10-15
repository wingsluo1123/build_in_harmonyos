#!/usr/bin/env python3
"""Consumer test for packaged tqdm 4.69.0 — real API (R34).

Progress-bar iteration + meter rendering on a non-TTY stream (OHOS device,
stdout redirected — must degrade to plain prints without TTY features).
"""
import io
import sys

site = sys.argv[1]
if site not in sys.path:
    sys.path.insert(0, site)

import tqdm  # noqa: E402


def main():
    # the recipe ships a minimal tqdm-4.69.0.dist-info, so version.py's
    # importlib.metadata lookup resolves exactly (no 4.70.1-style bump slip)
    assert tqdm.__version__ == "4.69.0", tqdm.__version__

    # 1. trange iteration, disabled (no TTY) — must complete silently
    total = 0
    for i in tqdm.trange(10, disable=True):
        total += i
    assert total == 45

    # 2. manual tqdm wrapper over an iterable with a non-TTY file stream
    buf = io.StringIO()
    out = []
    for ch in tqdm.tqdm("abc", file=buf, disable=False):
        out.append(ch)
    assert out == ["a", "b", "c"]

    # 3. format_meter rendering (pure function)
    meter = tqdm.tqdm.format_meter(n=5, total=10, elapsed=2.0)
    assert "50%" in meter, meter

    # 4. std (class) API with closing (render to StringIO — update() is a
    # no-op for n when disable=True, so keep it enabled with a dummy file)
    buf2 = io.StringIO()
    with tqdm.tqdm(total=3, file=buf2) as bar:
        for _ in range(3):
            bar.update(1)
        assert bar.n == 3

    print("test_tqdm: OK (version, trange, iterable wrap, format_meter, "
          "update)")


if __name__ == "__main__":
    main()
