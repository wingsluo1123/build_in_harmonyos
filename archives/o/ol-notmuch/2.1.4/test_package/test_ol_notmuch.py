import os
import sys


root = sys.argv[1]
lisp = os.path.join(root, "lisp", "ol-notmuch.el")
required = [
    lisp,
    os.path.join(root, "README.org"),
    os.path.join(root, "LICENSE"),
]

missing = [path for path in required if not os.path.isfile(path)]
if missing:
    raise SystemExit("missing packaged ol-notmuch files: " + ", ".join(missing))

with open(lisp, encoding="utf-8") as handle:
    content = handle.read()
if "(provide 'ol-notmuch)" not in content:
    raise SystemExit("ol-notmuch.el does not provide ol-notmuch")
if "org-link-set-parameters" not in content:
    raise SystemExit("ol-notmuch.el does not define the org link integration")

print("ol-notmuch Emacs Lisp files are packaged")
