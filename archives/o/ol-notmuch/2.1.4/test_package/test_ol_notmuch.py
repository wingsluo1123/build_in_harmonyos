import sys
from pathlib import Path


root = Path(sys.argv[1])
lisp = root / "lisp" / "ol-notmuch.el"
makefile = root / "Makefile"
required = [
    lisp,
    makefile,
    root / "README.org",
    root / "LICENSE",
]

missing = [str(path) for path in required if not path.is_file()]
if missing:
    raise SystemExit("missing packaged ol-notmuch files: " + ", ".join(missing))

content = lisp.read_text(encoding="utf-8")
for token in (
    "(require 'ol)",
    "(require 'notmuch)",
    "org-link-set-parameters",
    "(provide 'ol-notmuch)",
):
    if token not in content:
        raise SystemExit(f"ol-notmuch.el missing integration marker: {token}")

make_text = makefile.read_text(encoding="utf-8")
for token in ("lisp:", "autoloads:", "check-declare:", "batch-byte-compile", "loaddefs-generate"):
    if token not in make_text:
        raise SystemExit(f"upstream Makefile compile target missing: {token}")

print("ol-notmuch upstream compile entry and Emacs Lisp files are packaged")
