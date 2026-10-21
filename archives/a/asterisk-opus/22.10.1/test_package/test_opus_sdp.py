import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time


def sign_module(path):
    objcopy = shutil.which("llvm-objcopy")
    signer = shutil.which("binary-sign-tool")
    if not objcopy or not signer:
        raise RuntimeError("OHOS module signing requires llvm-objcopy and binary-sign-tool")
    subprocess.run([objcopy, "--remove-section", ".codesign", str(path)], check=True)
    subprocess.run([signer, "sign", "-inFile", str(path), "-outFile", str(path),
                    "-selfSign", "1"], check=True)
    path.chmod(0o755)


def main():
    package, core = map(Path, sys.argv[1:3])
    binary = core / "sbin" / "asterisk"
    if not binary.is_file():
        raise RuntimeError("The real Asterisk 22.10.1 executable is missing")
    with tempfile.TemporaryDirectory(prefix="opus-sdp-", dir=Path.cwd()) as directory:
        root = Path(directory)
        for name in ("etc", "modules", "run", "log", "data", "spool", "cache", "db"):
            (root / name).mkdir()
        shutil.copytree(core / "var/lib/asterisk/documentation", root / "data/documentation")
        sources = [package / "lib/asterisk/modules/res_format_attr_opus.so",
                   package / "share/asterisk-opus-tests/res_opus_consumer.so"]
        for source in sources:
            target = root / "modules" / source.name
            shutil.copyfile(source, target)
            if "--sign" in sys.argv[3:]:
                sign_module(target)
        config = root / "etc" / "asterisk.conf"
        config.write_text("[directories]\n" + "\n".join([
            f"astetcdir = {root / 'etc'}", f"astmoddir = {root / 'modules'}",
            f"astrundir = {root / 'run'}", f"astlogdir = {root / 'log'}",
            f"astvarlibdir = {root / 'data'}", f"astdatadir = {root / 'data'}",
            f"astspooldir = {root / 'spool'}", f"astcachedir = {root / 'cache'}",
            f"astdbdir = {root / 'db'}", "[options]", "documentation_language = en_US"
        ]) + "\n", encoding="utf-8")
        (root / "etc/modules.conf").write_text(
            "[modules]\nautoload=no\nrequire=res_format_attr_opus.so\n"
            "require=res_opus_consumer.so\n", encoding="utf-8")
        result = root / "result.txt"
        environment = os.environ.copy()
        environment["ASTERISK_OPUS_CONSUMER_RESULT"] = str(result)
        environment["LD_LIBRARY_PATH"] = str(core / "lib") + os.pathsep + environment.get("LD_LIBRARY_PATH", "")
        with (root / "asterisk.log").open("w+", encoding="utf-8") as log:
            process = subprocess.Popen([str(binary), "-f", "-g", "-n", "-C", str(config)],
                                       env=environment, stdout=log, stderr=subprocess.STDOUT)
            try:
                deadline = time.monotonic() + 60
                output = ""
                while process.poll() is None and time.monotonic() < deadline:
                    output = result.read_text(encoding="utf-8") if result.exists() else ""
                    if output.endswith("\n"):
                        break
                    time.sleep(0.2)
                output = result.read_text(encoding="utf-8") if result.exists() else ""
                if not output.startswith("PASS: Opus SDP parse, generation and roundtrip"):
                    log.flush()
                    log.seek(0)
                    raise RuntimeError("Real Asterisk Opus consumer failed: " + output + "\n" + log.read()[-12000:])
                print(output.strip())
            finally:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=10)


if __name__ == "__main__":
    main()
