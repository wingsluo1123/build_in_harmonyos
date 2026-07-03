# pipx

> Install and Run Python Applications in Isolated Environments

pipx is a command-line tool that helps you install and run Python applications
in isolated environments. It makes it easy to manage CLI tools without
polluting your system Python installation.

## Versions

| Version | Status | Date |
|---------|--------|------|
| 1.8.0 | published | 2026-07-01 |

## Details

- **Homepage**: https://pipx.pipa.io
- **Repository**: https://github.com/pypa/pipx
- **License**: MIT
- **Build system**: pip install (pure Python package)
- **Dependencies**: argcomplete, packaging, platformdirs, userpath

## OHOS Adaptation

pipx is a pure Python package with no C/C++ compilation steps. The OHOS
adaptation uses `python3 -m pip install` to build and install the package
into `lib/python3.12/site-packages/`. A wrapper script (`bin/pipx`) is
generated using `/system/bin/sh` shebang for OHOS compatibility.

### Key Notes

1. GitHub direct download not accessible from OHOS build environment;
   PyPI community mirror used instead (identical sha256).
2. `pip3` not in Conan build PATH; `python3 -m pip` used in conanfile.py.
3. Conan 2.x API: `self.dependencies["pipx"].package_folder` replaces
   deprecated `deps_cpp_info`.
