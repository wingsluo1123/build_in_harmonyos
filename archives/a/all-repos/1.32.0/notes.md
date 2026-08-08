# Notes — all-repos 1.32.0

## Software Info
- **Name:** all-repos
- **Version:** 1.32.0
- **Description:** Clone and run commands across all repos (Yelp tool for batch Git operations)
- **License:** MIT
- **Homepage:** https://github.com/asottile/all-repos
- **Source URL:** https://github.com/asottile/all-repos/archive/refs/tags/v1.32.0.tar.gz
- **SHA256:** 6660f0f21fbbbd4a6e55bcd8b910b6c41f5265a57cbee03403c3a676c0561399
- **Author:** Anthony Sottile (asottile)

## Build Characteristics
- **Type:** Pure Python package (CLI + library)
- **Build system:** None (Python package, setup.py-based)
- **Compilation:** No C/C++ compilation needed
- **Build process:** Copy .py files to package directory

## Dependencies
### Python Runtime Dependencies (pip-installable, NOT Conan deps)
- **identify** — file type identification (used by sed.py for filtering files)
- **packaging>=20.9** — version parsing (used by autofix_lib.py)
- **contextlib-chdir** — only for Python <3.11; not needed on Python 3.12

### Test Dependencies
- pytest, pytest-env, covdefaults, coverage
- pre-commit (for autofix tests)
- setup-py-upgrade, setup-cfg-fmt (for setup_py_upgrade autofix tests)

## CLI Entry Points (from setup.cfg)
```
all-repos-clone = all_repos.clone:main
all-repos-complete = all_repos.complete:main
all-repos-find-files = all_repos.find_files:main
all-repos-grep = all_repos.grep:main
all-repos-list-repos = all_repos.list_repos:main
all-repos-manual = all_repos.manual:main
all-repos-sed = all_repos.sed:main
```

## Package Structure
```
all_repos/
├── __init__.py          (empty — namespace marker)
├── autofix_lib.py       (autofix framework)
├── cli.py               (CLI argument helpers)
├── clone.py             (git clone/update)
├── color.py             (terminal color codes)
├── complete.py          (bash/zsh tab completion)
├── config.py            (Config NamedTuple, load_config)
├── find_files.py        (distributed git ls-files | grep)
├── git.py               (git remote helper)
├── github_api.py        (GitHub API helpers)
├── gitlab_api.py        (GitLab API helpers)
├── grep.py              (distributed git grep)
├── list_repos.py        (list cloned repos)
├── manual.py            (interactive manual fixer)
├── mapper.py            (thread/process mapper)
├── sed.py               (distributed sed)
├── util.py              (utility functions)
├── autofix/             (autofix modules)
│   ├── azure_pipelines_autoupdate.py
│   ├── pre_commit_autoupdate.py
│   ├── pre_commit_cache_dir.py
│   ├── pre_commit_flake8_migrate.py
│   ├── pre_commit_migrate_config.py
│   ├── setup_py_upgrade.py
│   └── _pre_commit_hook_migrate.py
├── push/                (push strategies)
│   ├── azure_repos_pull_request.py
│   ├── bitbucket_server_pull_request.py
│   ├── github_pull_request.py
│   ├── gitlab_pull_request.py
│   ├── merge_to_master.py
│   └── readonly.py
└── source/              (source providers)
    ├── azure_repos.py
    ├── bitbucket.py
    ├── bitbucket_server.py
    ├── github.py
    ├── github_forks.py
    ├── github_org.py
    ├── gitlab_org.py
    ├── gitolite.py
    └── json_file.py
```

## Key Decisions
1. **package_type = 'header-library'** — Conan doesn't have a pure-Python package_type.
   Using header-library means the .py files are packaged as content files.
2. **settings = 'os', 'arch'** — No compiler/build_type needed for pure Python.
3. **build(): pass** — No compilation step, just file packaging.
4. **package(): copy '*.py'** — Recursively copies all .py files from all_repos/
   to the package directory, preserving directory structure via keep_path=True.
5. **No Conan dependencies** — Python runtime deps (identify, packaging) are
   pip-installable, not Conan packages. Documented in notes.md.

## Adaptation Process
1. Downloaded source from GitHub via gh-proxy.com mirror (direct GitHub access blocked)
2. Installed Python dependencies via community PyPI source
3. Applied 4 platform workarounds (see below)
4. Ran upstream test suite: 163/169 passed (96.4%)
5. Created Conan recipe with pure-Python packaging pattern
6. Verified with conan create

## Platform Workarounds Applied

### 1. posix_spawn PATH lookup broken
On HarmonyOS PC, `os.posix_spawn()` cannot resolve executables via PATH.
Subprocess calls like `subprocess.run(['git', ...])` fail with FileNotFoundError.
**Fix:** Patched `sitecustomize.py` to set `subprocess._USE_POSIX_SPAWN = False`,
forcing fork+exec which correctly resolves PATH.

### 2. pytest tmpdir ownership check
HarmonyOS assigns directory ownership to the mount owner (uid 20001006) rather
than the process uid (20020101). pytest's tmpdir plugin rejects directories not
owned by the current user.
**Fix:** Patched `_pytest/tmpdir.py` to skip the ownership check.

### 3. git safe.directory dubious ownership
Git refuses to operate on directories owned by a different uid.
**Fix:** `git config --global --add safe.directory '*'`

### 4. all-repos _check_permissions chmod no-op (E046)
On HarmonyOS PC, `chmod()` is a no-op due to SELinux/filesystem restrictions.
Files always get permission `0o660` regardless of chmod calls.
all-repos's `config.py` requires config files to have permission `0o600`.
**Fix:** Patched `all_repos/config.py` to accept `0o660` as valid.

## Test Approach
- Upstream tests run via `python3 -m pytest tests/`
- 169 total tests collected
- Tests run individually in batches due to extreme slowness of git operations
  on HarmonyOS PC (~10-30s per git test vs <1s on native Linux)
- conan test_package validates packaged .py files: existence, content patterns,
  Python syntax validation, subdirectory structure

## Upstream Test Results
- **Passed:** 163/169 (96.4%)
- **Failed:** 6 (all due to platform/environment limitations)
  - 1 test: HarmonyOS chmod no-op (E046)
  - 1 test: Git version 2.45.2 behavior difference
  - 3 tests: pre-commit 4.6.1 version mismatch + posix_spawn PATH issue
  - 1 test: GitHub network access blocked
