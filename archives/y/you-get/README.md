# you-get

Command-line downloader for video/audio from YouTube, Bilibili and 100+ other web sites.
Pure Python CLI tool (no C/C++ extensions).

- Homepage: https://you-get.org/
- Upstream: https://github.com/soimort/you-get
- License: MIT

## OpenHarmony (OHOS) Adaptation Notes

### Language Preflight (R47 override)
The task was tagged `cpp`, but the source is pure Python (no C/C++ files).
Per user decision, adapted as a Python application (copy `src/you_get` →
site-packages + `bin/you-get` launcher; no wheel build), consistent with
pyparsing / check-jsonschema / laniakea-spark / bambam precedents. See
`0.4.1743/manifest.yaml` `r47_override`.

### dukpy dependency
Upstream `install_requires=['dukpy']`, but dukpy is only imported by
`src/you_get/extractors/youtube.py` (try/except ImportError → log + exit).
`you-get --version` and the common download flow do not need dukpy; the recipe
does not declare it as a Conan dependency (no recipe in the artifact repo, no
external pip in CI). YouTube downloads are limited as a known limitation.

### Runtime
The packaged `bin/you-get` launcher injects PYTHONPATH to the packaged
site-packages and runs `python3 -m you_get`. Requires a python3 interpreter at
runtime (provided by the consumer environment).

## Versions
- 0.4.1743 — first adaptation (status: built)
