#!/usr/bin/env python3
"""test_all_repos.py — R34 smoke test for the packaged all-repos library.

Validates package layout, then actually imports all_repos.color and calls
fmt()/fmtb() (no third-party deps). Exit 0 on success.
"""
import importlib
import os
import sys


def check_file_exists(path, description):
    if not os.path.isfile(path):
        print(f"FAIL: {description} — file not found: {path}")
        return False
    if os.path.getsize(path) <= 0:
        print(f"FAIL: {description} — file is empty: {path}")
        return False
    return True


def check_file_contains(path, pattern, description):
    if not os.path.isfile(path):
        print(f"FAIL: {description} — file not found: {path}")
        return False
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    if pattern not in content:
        print(f"FAIL: {description} — pattern '{pattern}' not found in {path}")
        return False
    return True


def exercise_color_api(lib_dir):
    """Import all_repos.color and call real APIs (R34)."""
    if lib_dir not in sys.path:
        sys.path.insert(0, lib_dir)

    try:
        color = importlib.import_module("all_repos.color")
    except Exception as exc:
        print(f"FAIL: import all_repos.color raised: {exc}")
        return False

    if not getattr(color, "BLUE_B", None):
        print("FAIL: all_repos.color.BLUE_B missing after import")
        return False

    colored = color.fmt("hello", color.BLUE_B, use_color=True)
    if color.BLUE_B not in colored or "hello" not in colored:
        print(f"FAIL: color.fmt(use_color=True) unexpected result: {colored!r}")
        return False

    plain = color.fmt("hello", color.BLUE_B, use_color=False)
    if plain != "hello":
        print(f"FAIL: color.fmt(use_color=False) unexpected result: {plain!r}")
        return False

    colored_b = color.fmtb(b"world", color.RED, use_color=True)
    if not isinstance(colored_b, (bytes, bytearray)) or b"world" not in colored_b:
        print(f"FAIL: color.fmtb unexpected result: {colored_b!r}")
        return False

    print(
        f"OK: imported all_repos.color and called fmt/fmtb "
        f"(BLUE_B={color.BLUE_B!r})"
    )
    return True


def main():
    if len(sys.argv) < 2:
        print("Usage: test_all_repos.py <package_folder>")
        return 1

    package_folder = sys.argv[1]
    lib_dir = os.path.join(package_folder, "lib")
    all_repos_dir = os.path.join(lib_dir, "all_repos")

    errors = 0

    # 1. Namespace marker
    init_path = os.path.join(all_repos_dir, "__init__.py")
    if not os.path.isfile(init_path):
        print(f"FAIL: all_repos/__init__.py not found at {init_path}")
        errors += 1
    else:
        print("OK: all_repos/__init__.py exists (namespace marker, may be empty)")

    # 2. cli.py
    cli_path = os.path.join(all_repos_dir, "cli.py")
    if not check_file_exists(cli_path, "cli.py existence"):
        errors += 1
    elif not check_file_contains(cli_path, "add_common_args", "cli.py CLI helpers"):
        errors += 1
    else:
        print("OK: all_repos/cli.py contains CLI argument helpers")

    # 3. config.py
    config_path = os.path.join(all_repos_dir, "config.py")
    if not check_file_exists(config_path, "config.py existence"):
        errors += 1
    elif not check_file_contains(config_path, "class Config", "config.py Config class"):
        errors += 1
    else:
        print("OK: all_repos/config.py contains Config class")

    # 4. clone.py
    clone_path = os.path.join(all_repos_dir, "clone.py")
    if not check_file_exists(clone_path, "clone.py existence"):
        errors += 1
    elif not check_file_contains(clone_path, "def main", "clone.py main function"):
        errors += 1
    elif not check_file_contains(clone_path, "git", "clone.py git operations"):
        errors += 1
    else:
        print("OK: all_repos/clone.py contains main() and git operations")

    # 5. grep.py
    grep_path = os.path.join(all_repos_dir, "grep.py")
    if not check_file_exists(grep_path, "grep.py existence"):
        errors += 1
    elif not check_file_contains(grep_path, "def grep", "grep.py grep function"):
        errors += 1
    else:
        print("OK: all_repos/grep.py contains grep function")

    # 6. find_files.py
    find_files_path = os.path.join(all_repos_dir, "find_files.py")
    if not check_file_exists(find_files_path, "find_files.py existence"):
        errors += 1
    elif not check_file_contains(find_files_path, "def find_files", "find_files.py function"):
        errors += 1
    else:
        print("OK: all_repos/find_files.py contains find_files function")

    # 7. mapper.py
    mapper_path = os.path.join(all_repos_dir, "mapper.py")
    if not check_file_exists(mapper_path, "mapper.py existence"):
        errors += 1
    elif not check_file_contains(mapper_path, "thread_mapper", "mapper.py thread_mapper"):
        errors += 1
    else:
        print("OK: all_repos/mapper.py contains thread_mapper")

    # 8. git.py
    git_path = os.path.join(all_repos_dir, "git.py")
    if not check_file_exists(git_path, "git.py existence"):
        errors += 1
    elif not check_file_contains(git_path, "def remote", "git.py remote function"):
        errors += 1
    else:
        print("OK: all_repos/git.py contains remote() function")

    # 9. Count .py files
    py_count = 0
    for root, _dirs, files in os.walk(all_repos_dir):
        for f in files:
            if f.endswith(".py"):
                py_count += 1
    if py_count < 5:
        print(f"FAIL: Expected >= 5 .py files in all_repos/, found {py_count}")
        errors += 1
    else:
        print(f"OK: Found {py_count} .py files in all_repos/ directory (>= 5)")

    # 10. Git-related content (no silent swallow of all exceptions)
    git_found = False
    for root, _dirs, files in os.walk(all_repos_dir):
        for f in files:
            if not f.endswith(".py"):
                continue
            filepath = os.path.join(root, f)
            try:
                with open(filepath, "r", encoding="utf-8") as fh:
                    if "git" in fh.read().lower():
                        git_found = True
                        break
            except OSError as exc:
                print(f"FAIL: cannot read {filepath}: {exc}")
                errors += 1
                break
        if git_found:
            break
    if not git_found:
        print("FAIL: No git-related content found in all_repos .py files")
        errors += 1
    else:
        print("OK: Git-related content found in all_repos .py files")

    # 11. sed.py
    sed_path = os.path.join(all_repos_dir, "sed.py")
    if not check_file_exists(sed_path, "sed.py existence"):
        errors += 1
    elif not check_file_contains(sed_path, "def main", "sed.py main function"):
        errors += 1
    else:
        print("OK: all_repos/sed.py contains main() function")

    # 12. color.py content
    color_path = os.path.join(all_repos_dir, "color.py")
    if not check_file_exists(color_path, "color.py existence"):
        errors += 1
    elif not check_file_contains(color_path, "BLUE_B", "color.py color constants"):
        errors += 1
    else:
        print("OK: all_repos/color.py contains color constants")

    # 13. list_repos.py
    list_repos_path = os.path.join(all_repos_dir, "list_repos.py")
    if not check_file_exists(list_repos_path, "list_repos.py existence"):
        errors += 1
    elif not check_file_contains(list_repos_path, "def main", "list_repos.py main"):
        errors += 1
    else:
        print("OK: all_repos/list_repos.py contains main() function")

    # 14. Subpackages
    for subdir in ["push", "source", "autofix"]:
        subdir_path = os.path.join(all_repos_dir, subdir, "__init__.py")
        if not os.path.isfile(subdir_path):
            print(f"FAIL: all_repos/{subdir}/__init__.py not found")
            errors += 1
        else:
            print(f"OK: all_repos/{subdir}/__init__.py exists")

    # 15. Layout
    if not os.path.isdir(all_repos_dir):
        print(f"FAIL: all_repos/ directory not found under lib/ at {all_repos_dir}")
        errors += 1
    else:
        print("OK: all_repos/ directory exists under lib/")

    # 16. Syntax check
    syntax_errors = 0
    for root, _dirs, files in os.walk(all_repos_dir):
        for f in files:
            if not f.endswith(".py"):
                continue
            filepath = os.path.join(root, f)
            try:
                with open(filepath, "r", encoding="utf-8") as fh:
                    source = fh.read()
                if source.strip():
                    compile(source, filepath, "exec")
            except SyntaxError as e:
                print(f"FAIL: Syntax error in {filepath}: {e}")
                syntax_errors += 1
    if syntax_errors > 0:
        errors += syntax_errors
    else:
        print("OK: All .py files pass Python syntax validation")

    # 17. R34 — real import + API call (blocking)
    if not exercise_color_api(lib_dir):
        errors += 1

    print()
    if errors > 0:
        print(f"FAILED: {errors} check(s) failed")
        return 1
    print("PASSED: All checks passed successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())
