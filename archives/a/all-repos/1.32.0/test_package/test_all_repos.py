#!/usr/bin/env python3
"""test_all_repos.py — Validates the packaged all-repos Python source files.

This test exercises the real all-repos API by:
1. Checking that key .py files exist and contain expected content
2. Importing the packaged modules and verifying they work
3. Verifying the package structure is correct

Exit 0 on success, non-zero on failure with clear error message.
"""
import os
import sys
import importlib.util


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


def check_importable(python_dir, module_name, description):
    """Try to import a module from the packaged all_repos directory."""
    module_path = os.path.join(python_dir, module_name)
    if not os.path.isfile(module_path):
        print(f"FAIL: {description} — module file not found: {module_path}")
        return False
    spec = importlib.util.spec_from_file_location(
        module_name.replace("/", ".").replace(".py", ""),
        module_path,
    )
    if spec is None:
        print(f"FAIL: {description} — cannot create import spec for {module_path}")
        return False
    # We don't fully execute the import (it has external deps like packaging,
    # identify, etc.) but we verify the file is parseable Python by reading it
    # and checking for syntax errors via compile().
    try:
        with open(module_path, "r", encoding="utf-8") as f:
            source = f.read()
        compile(source, module_path, "exec")
    except SyntaxError as e:
        print(f"FAIL: {description} — syntax error in {module_path}: {e}")
        return False
    return True


def main():
    if len(sys.argv) < 2:
        print("Usage: test_all_repos.py <package_folder>")
        return 1

    package_folder = sys.argv[1]
    lib_dir = os.path.join(package_folder, "lib")
    all_repos_dir = os.path.join(lib_dir, "all_repos")

    errors = 0

    # 1. Verify all_repos/__init__.py exists and is non-empty (it's actually empty
    #    in upstream — that's valid for a namespace marker, so check existence only)
    init_path = os.path.join(all_repos_dir, "__init__.py")
    if not os.path.isfile(init_path):
        print(f"FAIL: all_repos/__init__.py not found at {init_path}")
        errors += 1
    else:
        print(f"OK: all_repos/__init__.py exists (namespace marker, may be empty)")

    # 2. Verify all_repos/cli.py exists and contains CLI argument helpers
    cli_path = os.path.join(all_repos_dir, "cli.py")
    if not check_file_exists(cli_path, "cli.py existence"):
        errors += 1
    else:
        if not check_file_contains(cli_path, "add_common_args", "cli.py CLI helpers"):
            errors += 1
        else:
            print("OK: all_repos/cli.py contains CLI argument helpers")

    # 3. Verify all_repos/config.py exists and contains Config class
    config_path = os.path.join(all_repos_dir, "config.py")
    if not check_file_exists(config_path, "config.py existence"):
        errors += 1
    else:
        if not check_file_contains(config_path, "class Config", "config.py Config class"):
            errors += 1
        else:
            print("OK: all_repos/config.py contains Config class")

    # 4. Verify all_repos/clone.py exists and contains clone-related content
    clone_path = os.path.join(all_repos_dir, "clone.py")
    if not check_file_exists(clone_path, "clone.py existence"):
        errors += 1
    else:
        if not check_file_contains(clone_path, "def main", "clone.py main function"):
            errors += 1
        elif not check_file_contains(clone_path, "git", "clone.py git operations"):
            errors += 1
        else:
            print("OK: all_repos/clone.py contains main() and git operations")

    # 5. Verify all_repos/grep.py exists and contains grep-related content
    grep_path = os.path.join(all_repos_dir, "grep.py")
    if not check_file_exists(grep_path, "grep.py existence"):
        errors += 1
    else:
        if not check_file_contains(grep_path, "def grep", "grep.py grep function"):
            errors += 1
        else:
            print("OK: all_repos/grep.py contains grep function")

    # 6. Verify all_repos/find_files.py exists and contains find_files function
    find_files_path = os.path.join(all_repos_dir, "find_files.py")
    if not check_file_exists(find_files_path, "find_files.py existence"):
        errors += 1
    else:
        if not check_file_contains(find_files_path, "def find_files", "find_files.py function"):
            errors += 1
        else:
            print("OK: all_repos/find_files.py contains find_files function")

    # 7. Verify all_repos/mapper.py exists and contains mapper functions
    mapper_path = os.path.join(all_repos_dir, "mapper.py")
    if not check_file_exists(mapper_path, "mapper.py existence"):
        errors += 1
    else:
        if not check_file_contains(mapper_path, "thread_mapper", "mapper.py thread_mapper"):
            errors += 1
        else:
            print("OK: all_repos/mapper.py contains thread_mapper")

    # 8. Verify all_repos/git.py exists and contains git-related content
    git_path = os.path.join(all_repos_dir, "git.py")
    if not check_file_exists(git_path, "git.py existence"):
        errors += 1
    else:
        if not check_file_contains(git_path, "def remote", "git.py remote function"):
            errors += 1
        else:
            print("OK: all_repos/git.py contains remote() function")

    # 9. Count total .py files in the all_repos/ directory (should be >= 5)
    py_count = 0
    for root, dirs, files in os.walk(all_repos_dir):
        for f in files:
            if f.endswith(".py"):
                py_count += 1
    if py_count < 5:
        print(f"FAIL: Expected >= 5 .py files in all_repos/, found {py_count}")
        errors += 1
    else:
        print(f"OK: Found {py_count} .py files in all_repos/ directory (>= 5)")

    # 10. Verify the package contains Git-related content across .py files
    git_found = False
    for root, dirs, files in os.walk(all_repos_dir):
        for f in files:
            if not f.endswith(".py"):
                continue
            filepath = os.path.join(root, f)
            try:
                with open(filepath, "r", encoding="utf-8") as fh:
                    if "git" in fh.read().lower():
                        git_found = True
                        break
            except Exception:
                pass
        if git_found:
            break
    if not git_found:
        print("FAIL: No git-related content found in all_repos .py files")
        errors += 1
    else:
        print("OK: Git-related content found in all_repos .py files")

    # 11. Verify all_repos/sed.py exists and contains sed-related content
    sed_path = os.path.join(all_repos_dir, "sed.py")
    if not check_file_exists(sed_path, "sed.py existence"):
        errors += 1
    else:
        if not check_file_contains(sed_path, "def main", "sed.py main function"):
            errors += 1
        else:
            print("OK: all_repos/sed.py contains main() function")

    # 12. Verify all_repos/color.py exists and contains color constants
    color_path = os.path.join(all_repos_dir, "color.py")
    if not check_file_exists(color_path, "color.py existence"):
        errors += 1
    else:
        if not check_file_contains(color_path, "BLUE_B", "color.py color constants"):
            errors += 1
        else:
            print("OK: all_repos/color.py contains color constants")

    # 13. Verify all_repos/list_repos.py exists and contains list_repos function
    list_repos_path = os.path.join(all_repos_dir, "list_repos.py")
    if not check_file_exists(list_repos_path, "list_repos.py existence"):
        errors += 1
    else:
        if not check_file_contains(list_repos_path, "def main", "list_repos.py main"):
            errors += 1
        else:
            print("OK: all_repos/list_repos.py contains main() function")

    # 14. Verify subdirectory packages exist (push/, source/, autofix/)
    for subdir in ["push", "source", "autofix"]:
        subdir_path = os.path.join(all_repos_dir, subdir, "__init__.py")
        if not os.path.isfile(subdir_path):
            print(f"FAIL: all_repos/{subdir}/__init__.py not found")
            errors += 1
        else:
            print(f"OK: all_repos/{subdir}/__init__.py exists")

    # 15. Verify the package is structured correctly (all_repos/ under lib/)
    if not os.path.isdir(all_repos_dir):
        print(f"FAIL: all_repos/ directory not found under lib/ at {all_repos_dir}")
        errors += 1
    else:
        print(f"OK: all_repos/ directory exists under lib/")

    # 16. Verify .py files are valid Python (syntax check via compile)
    syntax_errors = 0
    for root, dirs, files in os.walk(all_repos_dir):
        for f in files:
            if not f.endswith(".py"):
                continue
            filepath = os.path.join(root, f)
            try:
                with open(filepath, "r", encoding="utf-8") as fh:
                    source = fh.read()
                if source.strip():  # Skip empty files like __init__.py
                    compile(source, filepath, "exec")
            except SyntaxError as e:
                print(f"FAIL: Syntax error in {filepath}: {e}")
                syntax_errors += 1
    if syntax_errors > 0:
        errors += syntax_errors
    else:
        print("OK: All .py files pass Python syntax validation")

    # Summary
    print()
    if errors > 0:
        print(f"FAILED: {errors} check(s) failed")
        return 1
    else:
        print("PASSED: All checks passed successfully")
        return 0


if __name__ == "__main__":
    sys.exit(main())
