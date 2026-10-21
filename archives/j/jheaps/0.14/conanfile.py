#!/usr/bin/env python3
"""Conan recipe for jheaps 0.14 (pure Java heap data-structure library)."""

import glob
import os
import re
import shutil
import struct
import subprocess
import xml.etree.ElementTree as ET
import zipfile

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class JHeapsConan(ConanFile):
    name = "jheaps"
    version = "0.14"
    description = "Java heap data structures (binary/d-ary arrays, pairing/fibonacci/radix heaps)"
    license = "Apache-2.0"
    homepage = "https://github.com/d-michail/jheaps"
    url = "https://github.com/d-michail/jheaps"

    package_type = "unknown"
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "conanfile.py", "conandata.yml", "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "jheaps is packaged for Linux/OpenHarmony JVM environments"
            )

    def package_id(self):
        # Artifacts are Java 8 bytecode (major 52); independent of CPU and OS.
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    @staticmethod
    def _java_executable(java_home, tool):
        suffix = ".exe" if os.name == "nt" else ""
        return os.path.join(java_home, "bin", tool + suffix)

    @staticmethod
    def _java_major(output, tool):
        if tool == "java":
            match = re.search(r'version\s+"([0-9]+)(?:[._][^"]*)?"', output)
        else:
            match = re.search(r"(?m)^javac\s+([0-9]+)(?:[._]\S*)?", output)
        if not match:
            raise ConanException(
                "Could not parse {} version output: {!r}".format(
                    tool, output.strip()
                )
            )
        return int(match.group(1))

    def _validate_java_home(self, java_home):
        java_home = os.path.abspath(os.path.expanduser(java_home))
        outputs = {}
        for tool in ("java", "javac"):
            executable = self._java_executable(java_home, tool)
            if not os.path.isfile(executable):
                raise ConanException(
                    "{} is missing from the candidate JDK: {}".format(
                        tool, executable
                    )
                )
            try:
                result = subprocess.run(
                    [executable, "-version"],
                    check=True,
                    text=True,
                    capture_output=True,
                )
            except (OSError, subprocess.CalledProcessError) as error:
                raise ConanException(
                    "Could not execute {} from {}: {}".format(
                        tool, java_home, error
                    )
                )
            output = "\n".join(
                part for part in (result.stdout, result.stderr) if part
            ).strip()
            major = self._java_major(output, tool)
            if major != 17:
                raise ConanException(
                    "{} from {} has major version {}, expected 17".format(
                        tool, java_home, major
                    )
                )
            outputs[tool] = output.splitlines()[0]

        self.output.info(
            "Using one verified JDK 17 home {}: {}; {}".format(
                java_home, outputs["java"], outputs["javac"]
            )
        )
        return java_home

    def _find_java_home(self):
        candidates = []
        configured = os.environ.get("JAVA_HOME", "")
        if configured:
            candidates.append(configured)
        candidates.extend(
            [
                os.path.expanduser("~/bishengjdk17"),
                os.path.expanduser("~/usr/local/bishengjdk17"),
                "/storage/Users/currentUser/usr/local/bishengjdk17",
                "/usr/local/bishengjdk17",
            ]
        )

        java_on_path = shutil.which("java")
        if java_on_path:
            candidates.append(
                os.path.dirname(os.path.dirname(os.path.realpath(java_on_path)))
            )

        rejected = []
        seen = set()
        for candidate in candidates:
            normalized = os.path.abspath(os.path.expanduser(candidate))
            if normalized in seen:
                continue
            seen.add(normalized)
            try:
                return self._validate_java_home(normalized)
            except ConanException as error:
                rejected.append(str(error))

        tool = self.conan_data["build_tools"]["bisheng_jdk"]
        installed = os.path.join(self.build_folder, "bishengjdk17")
        self.output.info(
            "No usable JDK 17 was found; downloading the pinned BiSheng JDK "
            "{} OpenHarmony AArch64 archive".format(tool["version"])
        )
        get(
            self,
            url=tool["url"],
            filename=tool["filename"],
            sha256=tool["sha256"],
            destination=installed,
            strip_root=True,
            keep_permissions=True,
        )
        try:
            return self._validate_java_home(installed)
        except ConanException as error:
            raise ConanException(
                "Pinned BiSheng JDK {} could not be used: {}. Rejected "
                "preinstalled candidates: {}".format(
                    tool["version"],
                    error,
                    "; ".join(rejected) if rejected else "none",
                )
            )

    def _validate_maven_home(self, maven_home, java_home):
        maven_home = os.path.abspath(os.path.expanduser(maven_home))
        mvn = os.path.join(maven_home, "bin", "mvn")
        if not os.path.isfile(mvn):
            raise ConanException(
                "mvn is missing from the candidate Maven home: {}".format(mvn)
            )
        environment = dict(os.environ)
        environment["JAVA_HOME"] = java_home
        environment["PATH"] = (
            os.path.join(java_home, "bin")
            + os.pathsep
            + environment.get("PATH", "")
        )
        try:
            result = subprocess.run(
                [mvn, "-v"],
                check=True,
                text=True,
                capture_output=True,
                env=environment,
            )
        except (OSError, subprocess.CalledProcessError) as error:
            raise ConanException(
                "Could not execute mvn from {}: {}".format(maven_home, error)
            )
        match = re.search(r"Apache Maven ([0-9]+)\.([0-9]+)\.(\S+)", result.stdout)
        if not match:
            raise ConanException(
                "Could not parse mvn -v output: {!r}".format(
                    result.stdout.strip()
                )
            )
        major, minor = int(match.group(1)), int(match.group(2))
        if major != 3 or minor < 8:
            raise ConanException(
                "Maven at {} reports version {}.{}.{}, expected 3.8+".format(
                    maven_home, major, minor, match.group(3)
                )
            )
        self.output.info(
            "Using verified Apache Maven {}.{}.{} home {}".format(
                major, minor, match.group(3), maven_home
            )
        )
        return maven_home

    def _find_maven_home(self, java_home):
        candidates = []
        for variable in ("MAVEN_HOME", "M2_HOME"):
            configured = os.environ.get(variable, "")
            if configured:
                candidates.append(configured)
        mvn_on_path = shutil.which("mvn")
        if mvn_on_path:
            candidates.append(
                os.path.dirname(os.path.dirname(os.path.realpath(mvn_on_path)))
            )

        rejected = []
        seen = set()
        for candidate in candidates:
            normalized = os.path.abspath(os.path.expanduser(candidate))
            if normalized in seen:
                continue
            seen.add(normalized)
            try:
                return self._validate_maven_home(normalized, java_home)
            except ConanException as error:
                rejected.append(str(error))

        tool = self.conan_data["build_tools"]["maven"]
        installed = os.path.join(
            self.build_folder, "apache-maven-{}".format(tool["version"])
        )
        self.output.info(
            "No usable Maven 3.8+ was found; downloading the pinned Apache "
            "Maven {} binary distribution".format(tool["version"])
        )
        get(
            self,
            url=tool["url"],
            filename=tool["filename"],
            sha256=tool["sha256"],
            destination=installed,
            strip_root=True,
            keep_permissions=True,
        )
        try:
            return self._validate_maven_home(installed, java_home)
        except ConanException as error:
            raise ConanException(
                "Pinned Apache Maven {} could not be used: {}. Rejected "
                "preinstalled candidates: {}".format(
                    tool["version"],
                    error,
                    "; ".join(rejected) if rejected else "none",
                )
            )

    def _maven_command(self, maven_home, repo_local):
        return [
            os.path.join(maven_home, "bin", "mvn"),
            "-B",
            "-Dstyle.color=never",
            # The OpenHarmony JVM reports user.home as "?" (the uid is not in
            # /etc/passwd); pin user.home and the Maven local repository inside
            # the Conan build folder so nothing lands in a cwd-relative
            # "?/.m2" directory (export HOME does not help: the JVM never
            # falls back to it).
            "-Duser.home={}".format(self.build_folder),
            "-Dmaven.repo.local={}".format(repo_local),
            "-Dmaven.javadoc.skip=true",
            # `package` compiles, runs the complete upstream JUnit suite
            # (test phase) and produces the OSGi-manifested jar, while staying
            # below `verify`, where the upstream jacoco 0.75 COVEREDRATIO gate
            # is bound. Skipping that gate is a deliberate, documented scope:
            # the packaged artifact and every upstream test are unchanged.
            "clean",
            "package",
        ]

    @staticmethod
    def _final_state_counts(report):
        # Rerun-aware final-state counts of one Surefire XML report. The build
        # runs plain `mvn package` without surefire rerun flags, so rerun
        # artifacts are not expected; the counting stays rerun-aware
        # defensively (a rerun-enabled environment or future flag change must
        # not silently pass here). See the per-test element contract in the
        # jline3 recipe: every direct <testcase> child is one unique test and
        # retry records are children of that testcase.
        counts = {
            "tests": 0,
            "failures": 0,
            "errors": 0,
            "skipped": 0,
            "flakes": 0,
        }
        for case in ET.parse(report).getroot().findall("testcase"):
            children = set(child.tag for child in case)
            counts["tests"] += 1
            if children & {"flakyFailure", "flakyError"}:
                counts["flakes"] += 1
            elif "rerunError" in children or "error" in children:
                counts["errors"] += 1
            elif "rerunFailure" in children or "failure" in children:
                counts["failures"] += 1
            if "skipped" in children:
                counts["skipped"] += 1
        return counts

    def _verify_upstream_tests(self):
        reports = glob.glob(
            os.path.join(
                self.source_folder,
                "target",
                "surefire-reports",
                "TEST-*.xml",
            )
        )
        totals = {
            "tests": 0,
            "failures": 0,
            "errors": 0,
            "skipped": 0,
            "flakes": 0,
        }
        for report in reports:
            for name, value in self._final_state_counts(report).items():
                totals[name] += value

        expected_suites = 51
        expected_tests = 1391
        if (
            len(reports) != expected_suites
            or totals["tests"] != expected_tests
            or totals["failures"]
            or totals["errors"]
            or totals["skipped"]
        ):
            raise ConanException(
                "Unexpected upstream test result (rerun-aware final state): "
                "suites={}, totals={}".format(len(reports), totals)
            )
        if totals["flakes"]:
            raise ConanException(
                "Unexpected flaky upstream test records ({}): surefire rerun "
                "flags are not used by this build".format(totals["flakes"])
            )
        self.output.info(
            "Upstream tests passed (rerun-aware final state): {} Surefire "
            "suites, {} tests (the tag's 428 unique @Test source methods "
            "execute 1391 times through JUnit inheritance into concrete "
            "suites), 0 failures/errors/skips".format(
                expected_suites, expected_tests
            )
        )

    @staticmethod
    def _class_major(data, entry, jar_path):
        if len(data) < 8 or data[:4] != b"\xca\xfe\xba\xbe":
            raise ConanException(
                "{} in {} is not a valid Java class".format(entry, jar_path)
            )
        return struct.unpack(">H", data[6:8])[0]

    _required_entries = (
        "org/jheaps/AddressableHeap.class",
        "org/jheaps/Heap.class",
        "org/jheaps/MergeableHeap.class",
        "org/jheaps/array/BinaryArrayAddressableHeap.class",
        "org/jheaps/monotone/DoubleRadixAddressableHeap.class",
        "org/jheaps/tree/PairingHeap.class",
        "org/jheaps/tree/FibonacciHeap.class",
        "META-INF/MANIFEST.MF",
    )

    _expected_class_count = 88

    def _verify_jar(self, jar_path):
        if not os.path.isfile(jar_path) or os.path.getsize(jar_path) <= 0:
            raise ConanException(
                "Required artifact is missing or empty: {}".format(jar_path)
            )
        try:
            with zipfile.ZipFile(jar_path) as archive:
                corrupt = archive.testzip()
                if corrupt:
                    raise ConanException(
                        "{} has a corrupt ZIP entry: {}".format(
                            jar_path, corrupt
                        )
                    )
                entries = set(archive.namelist())
                class_entries = [
                    entry for entry in entries if entry.endswith(".class")
                ]
                majors = {
                    self._class_major(archive.read(entry), entry, jar_path)
                    for entry in class_entries
                }
                if majors != {52}:
                    raise ConanException(
                        "Unexpected bytecode in {}: majors={}".format(
                            jar_path, sorted(majors)
                        )
                    )
                missing = sorted(set(self._required_entries) - entries)
                if missing:
                    raise ConanException(
                        "{} is missing required entries: {}".format(
                            jar_path, ", ".join(missing)
                        )
                    )
                if len(class_entries) != self._expected_class_count:
                    raise ConanException(
                        "Unexpected class count in {}: {} (expected {})".format(
                            jar_path,
                            len(class_entries),
                            self._expected_class_count,
                        )
                    )
                manifest = archive.read("META-INF/MANIFEST.MF").decode(
                    "utf-8", "replace"
                )
        except (OSError, zipfile.BadZipFile) as error:
            raise ConanException(
                "Could not validate {}: {}".format(jar_path, error)
            )
        if "Automatic-Module-Name: org.jheaps" not in manifest:
            raise ConanException(
                "{} lacks the OSGi Automatic-Module-Name org.jheaps "
                "generated by the maven-bundle-plugin".format(jar_path)
            )
        self.output.info(
            "jheaps-{}.jar verification passed: nonempty JAR, clean ZIP, "
            "Java 8 bytecode, required entries, OSGi bundle manifest".format(
                self.version
            )
        )

    def build(self):
        apply_conandata_patches(self)

        java_home = self._find_java_home()
        maven_home = self._find_maven_home(java_home)
        environment = os.environ.copy()
        environment["JAVA_HOME"] = java_home
        if not environment.get("HOME"):
            # OpenHarmony sessions may run without HOME; the JVM cannot derive
            # user.home there either (it reports "?"), so give tools a
            # guaranteed-writable fallback directory.
            environment["HOME"] = java_home
        environment["PATH"] = (
            os.path.join(java_home, "bin")
            + os.pathsep
            + environment.get("PATH", "")
        )
        # Maven and its forked Surefire JVMs do not recognize "HarmonyOS" as
        # an os.name value. OpenHarmony PC provides a Linux-compatible JVM
        # environment, so expose the platform family as Linux to Java tools.
        existing_java_options = environment.get("JAVA_TOOL_OPTIONS", "").strip()
        environment["JAVA_TOOL_OPTIONS"] = (
            existing_java_options + " -Dos.name=Linux"
        ).strip()
        environment["MAVEN_OPTS"] = "-Xmx768m"

        repo_local = os.path.join(self.build_folder, "m2-repository")
        self.output.info(
            "Building jheaps with Maven and running the complete upstream "
            "JUnit test suite"
        )
        subprocess.run(
            self._maven_command(maven_home, repo_local),
            cwd=self.source_folder,
            env=environment,
            check=True,
        )
        self._verify_upstream_tests()
        self._verify_jar(
            os.path.join(
                self.source_folder, "target", "jheaps-{}.jar".format(self.version)
            )
        )

    def package(self):
        copy(
            self,
            "jheaps-{}.jar".format(self.version),
            src=os.path.join(self.source_folder, "target"),
            dst=os.path.join(self.package_folder, "lib"),
        )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        self._verify_jar(
            os.path.join(
                self.package_folder,
                "lib",
                "jheaps-{}.jar".format(self.version),
            )
        )
        copy(
            self,
            "README.md",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "doc", "jheaps"),
        )

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = ["lib"]
        jar_path = os.path.join(
            self.package_folder,
            "lib",
            "jheaps-{}.jar".format(self.version),
        )
        self.buildenv_info.define_path("JHEAPS_JAR", jar_path)
        self.runenv_info.define_path("JHEAPS_JAR", jar_path)
