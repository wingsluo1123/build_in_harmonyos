"""Run native feature and original upstream tests using private OHOS copies."""
import os
from pathlib import Path
import shutil
import subprocess
import sys


def main():
    package, build, source, target_os = sys.argv[1:]
    # Verify the installed bytes before re-signing any private test copy.
    if target_os == "OHOS":
        subprocess.run([str(Path(package) / "bin/groonga"), "--version"],
                       check=True, timeout=30)
    stage = Path(build) / "staged-groonga"
    if stage.exists():
        shutil.rmtree(stage)
    shutil.copytree(package, stage, symlinks=False)
    if target_os == "OHOS":
        tools = [shutil.which(name) for name in ("llvm-objcopy", "binary-sign-tool")]
        if not all(tools):
            raise RuntimeError("OHOS signing tools are required")
        for path in sorted(stage.rglob("*")):
            if not path.is_file():
                continue
            with path.open("rb") as stream:
                elf = stream.read(4) == b"\x7fELF"
            if elf:
                subprocess.run([tools[0], "--remove-section", ".codesign", str(path)], check=True)
                subprocess.run([tools[1], "sign", "-inFile", str(path),
                                "-outFile", str(path), "-selfSign", "1"], check=True)
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = str(stage / "lib") + os.pathsep + env.get("LD_LIBRARY_PATH", "")
    env["GRN_PLUGINS_DIR"] = str(stage / "lib/groonga/plugins")
    env["GRN_QUERY_EXPANDER_TSV_SYNONYMS_FILE"] = str(stage / "etc/groonga/synonyms.tsv")
    subprocess.run(["ctest", "--output-on-failure"], cwd=build, env=env, check=True, timeout=90)
    subprocess.run([sys.executable, str(Path(source) / "run_selected_upstream.py"),
                    "--groonga", str(stage / "bin/groonga"),
                    "--fixtures", str(Path(source) / "upstream/test/command/suite"),
                    "--inventory", str(Path(source) / "selected-upstream-inventory.json"),
                    "--output", str(Path(build) / "upstream-results")], env=env, check=True, timeout=600)


if __name__ == "__main__":
    main()
