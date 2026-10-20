#!/usr/bin/env python3
"""Reconcile the pinned source inventory with the declared CMake test suite."""
import argparse
import ast
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import tarfile


SOURCE_SHA256 = "fc025cae7246b780ba7ba85deeff0386ec272d901185058c0b5e614543d5676c"
SOURCE_COMMIT = "2b69aed630e26fb2c700bba8c45f3bd012371c5c"


def audit(archive, manifest):
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    if digest != SOURCE_SHA256:
        raise ValueError("Source archive SHA256 differs from the pinned recipe")
    with tarfile.open(archive, "r:gz") as source:
        members = {m.name.split("/", 1)[1]: m for m in source
                   if m.isfile() and "/" in m.name}

        def read(name):
            return source.extractfile(members[name]).read()

        raw = sorted(n for n in members if n.startswith("src/") and n.endswith("-test.cc"))
        library = [n for n in raw if str(PurePosixPath(n).parent / "Makefile") in members]
        probes = sorted(set(raw) - set(library))
        generator = read("cmake/gen_cmake_skeleton.py").decode()
        assignment = next(node for node in ast.parse(generator).body
                          if isinstance(node, ast.Assign)
                          and any(isinstance(t, ast.Name) and t.id == "EXCLUDE_FILES"
                                  for t in node.targets))
        excluded_names = set(ast.literal_eval(assignment.value))
        cmake = read("CMakeLists.txt").decode()
        root_directories = set(re.findall(r"^\s*add_subdirectory\((src/[^)\s]+)\)", cmake, re.M))
        cmake_sources = {n for n in library if str(PurePosixPath(n).parent) in root_directories
                         and PurePosixPath(n).name not in excluded_names}
        text = manifest.read_text(encoding="utf-8")
        declared = re.findall(r"^  source: (src/[^\r\n]+)$", text.split("test_package_tests:")[0], re.M)
        if len(declared) != len(set(declared)) or set(declared) != cmake_sources:
            raise ValueError("MANIFEST sources differ from the original upstream CMake selection")
        unregistered = sorted(set(library) - cmake_sources)
        expected = ["src/lm/kenlm-test.cc", "src/sgmm2/am-sgmm2-test.cc",
                    "src/sgmm2/estimate-am-sgmm2-test.cc", "src/sgmm2/fmllr-sgmm2-test.cc"]
        if unregistered != expected or len(library) != 129 or len(cmake_sources) != 125:
            raise ValueError("Unexpected upstream inventory; investigate before updating counts")
        evidence_files = ["CMakeLists.txt", "cmake/gen_cmake_skeleton.py", "src/Makefile",
                          "src/lm/Makefile", "src/sgmm2/Makefile", "src/probe/exp-test.cc",
                          "src/probe/mkl-test.cc"]
        return {
            "source_commit": SOURCE_COMMIT,
            "source_archive_sha256": digest,
            "counting_unit": "Library *-test.cc source programs; not assertions or executed cases",
            "raw_src_test_sources": len(raw),
            "upstream_library_test_sources": len(library),
            "original_cmake_selected_tests": len(cmake_sources),
            "manifest_registered_tests": len(declared),
            "outside_current_configuration": len(unregistered),
            "scope_note": "129 is the source inventory; actual registered/executed suite is 125. "
                          "The four optional tests were not executed and are not passes or CTest skips.",
            "library_tests": [
                {"source": n, "sha256": hashlib.sha256(read(n)).hexdigest(),
                 "registered_in_current_configuration": n in cmake_sources,
                 "selection_reason": "selected by upstream CMake" if n in cmake_sources else
                     "upstream generator EXCLUDE_FILES; Makefile requires KENLM_ROOT" if n.endswith("kenlm-test.cc") else
                     "sgmm2 is an optional Makefile extension; upstream root CMake does not add src/sgmm2"}
                for n in library
            ],
            "configuration_probes_not_library_suite": probes,
            "upstream_evidence_sha256": {n: hashlib.sha256(read(n)).hexdigest() for n in evidence_files},
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_archive", type=Path)
    parser.add_argument("--manifest", type=Path,
                        default=Path(__file__).resolve().parents[1] / "test_package/MANIFEST.yml")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = json.dumps(audit(args.source_archive, args.manifest), ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(result, encoding="utf-8", newline="\n")
    else:
        print(result, end="")


if __name__ == "__main__":
    main()
