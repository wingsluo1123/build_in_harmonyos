# dill 0.4.1 adaptation

## Scope and source

Task 15169, assigned account 2301_79503900, team 北京理工大学/天天开心, branch feat/dill-0.4.1. Official PyPI sdist SHA256 matches conandata.yml. Python >=3.9; no mandatory third-party runtime dependency; setuptools/84.0.0 is the published build tool. Optional graph/profile extras are not enabled.

## Problem and remedy

| Problem | Cause | Remedy |
| --- | --- | --- |
| Parent can import dill but 30 fresh child scripts fail with ModuleNotFoundError | python -m finds the package through current directory; script-mode children search their test-script directory | Build a private installed package, export its root through inherited PYTHONPATH, and execute the suite from a separate directory with -P |
| Source-directory import could mask missing distribution files | Current directory precedes installation search path | Check dill.__file__ under staged install and run consumers against Conan package root |
| setuptools build_scripts would bake build interpreter path into installed commands | Installation interpreter paths differ across workers | Keep upstream script bodies as resources; package relative Python launchers with /usr/bin/env python3 and help |

No upstream source/test patch; launchers are recipe-owned additions. Count tests in upstream runner units: 30 distinct child script processes, not test function count or assertion count. Five conditional NumPy/SymPy branches are unavailable and explicitly listed in MANIFEST.yml; no claim of all optional coverage.

## Verification

See reports/validation-summary.md and reports/path-b-evidence.md. Raw logs and generated CI receipts are retained outside committed files. Local device validation, remote CI, official knowledge admission, review, merge and release are distinct states.

## 编译结束

本地构建、上游脚本30/30、消费者14/14、W3五级门禁通过。远端CI/审核/知识入库/合并/发布另行核验。
