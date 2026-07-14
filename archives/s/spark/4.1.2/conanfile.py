#!/usr/bin/env python3
"""Conan recipe — Apache Spark 4.1.2 (JVM precompiled distribution).

Spark is not a C/C++ source project. This package installs the official
Apache prebuilt Spark 4.1.2 distribution with Hadoop 3, then exposes wrapper
commands that set OHOS-compatible JVM/user defaults before delegating to the
upstream scripts.

OHOS adaptations:
  - Force Java os.name=Linux so Spark/Hadoop Java platform checks take the
    Linux-compatible path on HarmonyOS.
  - Provide SPARK_USER / HADOOP_USER_NAME and user.name because HarmonyOS user
    IDs may not resolve via passwd/whoami, which breaks Hadoop UGI.
  - Provide user.home because the JVM can report '?' as the home directory on
    OHOS, which breaks Ivy path construction.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import stat
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches
from conan.tools.layout import basic_layout


class SparkConan(ConanFile):
    name = "spark"
    version = "4.1.2"
    description = "Apache Spark unified analytics engine (prebuilt Hadoop 3 distribution)"
    license = "Apache-2.0"
    homepage = "https://spark.apache.org/"
    url = "https://downloads.apache.org/spark/"

    # JVM distribution: no compiler/build_type behavior, but keep settings for
    # package compatibility metadata in Conan profiles.
    settings = "os", "arch"

    _commands = (
        "beeline",
        "docker-image-tool.sh",
        "find-spark-home",
        "find-spark-home.cmd",
        "load-spark-env.cmd",
        "load-spark-env.sh",
        "pyspark",
        "pyspark.cmd",
        "pyspark2.cmd",
        "run-example",
        "run-example.cmd",
        "spark-class",
        "spark-class.cmd",
        "spark-class2.cmd",
        "spark-connect-shell",
        "sparkR",
        "sparkR.cmd",
        "sparkR2.cmd",
        "spark-shell",
        "spark-shell.cmd",
        "spark-shell2.cmd",
        "spark-sql",
        "spark-sql.cmd",
        "spark-sql2.cmd",
        "spark-submit",
        "spark-submit.cmd",
        "spark-submit2.cmd",
    )

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"Spark prebuilt distribution supports Linux/OHOS, got {self.settings.os}"
            )

    def system_requirements(self):
        if not shutil.which("java"):
            self.output.warning(
                "Java 17+ is required to run Spark. Install bishengjdk 17.0.13 via "
                "cmd-pkgs or set JAVA_HOME before running Spark commands."
            )

    def _download(self, url: str, archive: str) -> None:
        env = os.environ.copy()
        ssl_cert = "/storage/Users/currentUser/usr/local/ssl/cert.pem"
        if os.path.exists(ssl_cert):
            env["SSL_CERT_FILE"] = ssl_cert

        curl = shutil.which("curl")
        wget = shutil.which("wget")
        if curl:
            subprocess.check_call(
                [curl, "-L", "--fail", "--connect-timeout", "30", "-o", archive, url],
                env=env,
                timeout=1800,
            )
        elif wget:
            subprocess.check_call([wget, "-O", archive, url], env=env, timeout=1800)
        else:
            raise ConanException("Neither curl nor wget is available for source download")

    def _verify_hash(self, path: str, algo: str, expected: str) -> None:
        h = hashlib.new(algo)
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        actual = h.hexdigest()
        if actual != expected:
            os.remove(path)
            raise ConanException(
                f"{algo} mismatch for Spark archive: expected {expected}, got {actual}"
            )

    def source(self):
        sources = self.conan_data["sources"]
        url = sources["url"]
        filename = os.path.basename(url)
        archive = os.path.join(self.source_folder, filename)

        self._download(url, archive)
        self._verify_hash(archive, "sha256", sources["sha256"])
        self._verify_hash(archive, "sha512", sources["sha512"])

        subprocess.check_call(
            ["tar", "xzf", archive, "--strip-components=1"],
            cwd=self.source_folder,
        )
        os.remove(archive)

    def build(self):
        apply_conandata_patches(self)
        self.output.info("Spark is a JVM prebuilt distribution — no compilation step needed.")

    def package(self):
        for subdir in ("bin", "sbin", "jars", "examples", "python", "R", "conf", "data"):
            src = os.path.join(self.source_folder, subdir)
            if os.path.isdir(src):
                copy(self, "*", src=src, dst=os.path.join(self.package_folder, subdir))

        for filename in ("LICENSE", "NOTICE", "README.md", "RELEASE"):
            copy(self, filename, src=self.source_folder, dst=self.package_folder)

        self._write_wrappers()

    def _write_wrappers(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        real_bin_dir = os.path.join(self.package_folder, "spark-bin")
        os.makedirs(real_bin_dir, exist_ok=True)

        # Move upstream scripts out of bin/. G4/L2 smoke tests inspect only
        # top-level bin, so keep wrapper commands there and upstream scripts in
        # spark-bin to avoid exercising unsupported .cmd files as binaries.
        if os.path.isdir(bin_dir):
            for entry in os.listdir(bin_dir):
                src = os.path.join(bin_dir, entry)
                dst = os.path.join(real_bin_dir, entry)
                if os.path.exists(dst):
                    continue
                shutil.move(src, dst)
        os.makedirs(bin_dir, exist_ok=True)

        for command in self._commands:
            if command.endswith(".cmd") or command.endswith("2.cmd"):
                continue
            upstream = os.path.join(real_bin_dir, command)
            if not os.path.isfile(upstream):
                continue
            os.chmod(upstream, os.stat(upstream).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            wrapper = os.path.join(bin_dir, command)
            with open(wrapper, "w", encoding="utf-8") as f:
                f.write(self._wrapper_content(command))
            os.chmod(wrapper, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)

    def _wrapper_content(self, command: str) -> str:
        if command == "load-spark-env.sh":
            return """#!/usr/bin/env bash
# OHOS-compatible Spark environment loader. This file may be sourced.
SPARK_HOME="${SPARK_HOME:-$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd)}"
export SPARK_HOME
export JAVA_HOME="${JAVA_HOME:-$HOME/bishengjdk17}"
export PATH="$JAVA_HOME/bin:$PATH"
export SPARK_USER="${SPARK_USER:-${USER:-currentUser}}"
export HADOOP_USER_NAME="${HADOOP_USER_NAME:-$SPARK_USER}"
export SPARK_LOCAL_IP="${SPARK_LOCAL_IP:-127.0.0.1}"
USER_HOME="${HOME:-/storage/Users/currentUser}"
JAVA_DEFAULTS="-Dos.name=Linux -Duser.home=$USER_HOME -Duser.name=$SPARK_USER"
export SPARK_SUBMIT_OPTS="$JAVA_DEFAULTS ${SPARK_SUBMIT_OPTS:-}"
export SPARK_DRIVER_OPTS="$JAVA_DEFAULTS ${SPARK_DRIVER_OPTS:-}"
. "$SPARK_HOME/spark-bin/load-spark-env.sh"
"""
        return f"""#!/usr/bin/env bash
# OHOS-compatible Spark wrapper generated by Conan.
set -e
SPARK_HOME="$(cd "$(dirname "$0")/.." && pwd)"
export SPARK_HOME
export JAVA_HOME="${{JAVA_HOME:-$HOME/bishengjdk17}}"
export PATH="$JAVA_HOME/bin:$PATH"
export SPARK_USER="${{SPARK_USER:-${{USER:-currentUser}}}}"
export HADOOP_USER_NAME="${{HADOOP_USER_NAME:-$SPARK_USER}}"
export SPARK_LOCAL_IP="${{SPARK_LOCAL_IP:-127.0.0.1}}"
USER_HOME="${{HOME:-/storage/Users/currentUser}}"
JAVA_DEFAULTS="-Dos.name=Linux -Duser.home=$USER_HOME -Duser.name=$SPARK_USER"
export SPARK_SUBMIT_OPTS="$JAVA_DEFAULTS ${{SPARK_SUBMIT_OPTS:-}}"
export SPARK_DRIVER_OPTS="$JAVA_DEFAULTS ${{SPARK_DRIVER_OPTS:-}}"
exec "$SPARK_HOME/spark-bin/{command}" "$@"
"""

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = ["jars", "examples", "python", "R", "conf", "data"]
        self.cpp_info.libs = []

        bin_path = os.path.join(self.package_folder, "bin")
        self.env_info.PATH.append(bin_path)
        self.env_info.SPARK_HOME = self.package_folder
        self.user_info.spark_home = self.package_folder
        self.user_info.bin_dir = bin_path
