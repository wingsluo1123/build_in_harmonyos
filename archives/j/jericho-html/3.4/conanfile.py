#!/usr/bin/env python3
"""Conan recipe — jericho-html 3.4 (Java source compilation).

Downloads upstream sources jar from Maven Central (official artifact),
compiles with javac (JDK 17, source/target 7 per upstream POM), runs the
upstream JUnit 4 test suite (50 runnable @Test methods) in build(), and
packages the resulting JAR.

Upstream ships tests only in the SourceForge project zip (Ant build, no
mvnw). The test sources are therefore vendored under upstream-tests/
(verbatim from upstream 3.4, triple-licensed EPL/LGPL/Apache-2.0, same
license as the library itself).

Source: Maven Central net.htmlparser.jericho:jericho-html:3.4
License: EPL-1.0 / LGPL-2.1 / Apache-2.0 (triple license, pick one)
Build system: javac + jar (upstream uses Ant; sources jar is official)
Upstream tests: 50 runnable @Test methods via net.htmlparser.jericho.TestSuite
  (StAXTest is fully commented out upstream — requires JDK 1.6 StAX;
   StreamedSourceHugeFileTest's 2 tests are self-disabled upstream)

R28: test_package/ included
R32: validate() checks settings.os in (Linux, OHOS)
R34: test_package calls jericho-html API (Source/Element/TextExtractor)
R38: library package (no commands.json needed)
"""
import os
import shutil
import stat

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, download, apply_conandata_patches


class JerichoHtmlConan(ConanFile):
    name = "jericho-html"
    version = "3.4"
    description = (
        "Jericho HTML Parser: Java library for analysis and manipulation of "
        "parts of an HTML document, including server-side tags, while "
        "reproducing verbatim any unrecognised or invalid HTML"
    )
    license = ("EPL-1.0", "LGPL-2.1-only", "Apache-2.0")
    homepage = "http://jericho.htmlparser.net"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # Java 包：compiler/build_type 不参与实际构建，但 OHOS CI L0p 门禁要求四项齐全
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        copy(self, "upstream-tests/*", self.recipe_folder, self.export_sources_folder)
        copy(self, "license/*", self.recipe_folder, self.export_sources_folder)

    def layout(self):
        pass

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"jericho-html does not support OS: {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=False)

    def _ensure_java(self):
        """Find bishengjdk 17 in the environment, or auto-install via cmd-pkgs.

        Checks (in order):
          1. JAVA_HOME environment variable
          2. ~/bishengjdk17 and ~/usr/local/bishengjdk17 (standard cmd-pkgs paths)
          3. java on PATH
          4. Auto-install via cmd-pkgs install-jdk.sh (CI workers may lack JDK)

        Returns the JAVA_HOME path. Raises ConanInvalidConfiguration if all fail.
        """
        java_home = os.environ.get("JAVA_HOME", "")
        if java_home and os.path.isfile(os.path.join(java_home, "bin", "java")):
            self.output.info("Java found via JAVA_HOME=" + java_home)
            return java_home

        for candidate in [
            os.path.expanduser("~/bishengjdk17"),
            os.path.expanduser("~/usr/local/bishengjdk17"),
        ]:
            if os.path.isfile(os.path.join(candidate, "bin", "java")):
                self.output.info("Java found at " + candidate)
                return candidate

        java_in_path = shutil.which("java")
        if java_in_path:
            candidate = os.path.dirname(os.path.dirname(os.path.realpath(java_in_path)))
            self.output.info("Java found in PATH at " + candidate)
            return candidate

        self.output.info("Java not found — installing bishengjdk 17.0.13 via cmd-pkgs...")
        install_url = (
            "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs"
            "/releases/download/pkgs/install-jdk.sh"
        )
        script_path = os.path.join(os.path.expanduser("~"), ".install-jdk.sh")
        self.run('curl -fsSL -o "{}" "{}"'.format(script_path, install_url))
        self.run('sh "{}" 17.0.13'.format(script_path))

        java_home = os.path.expanduser("~/bishengjdk17")
        if os.path.isfile(os.path.join(java_home, "bin", "java")):
            self.output.info("bishengjdk 17.0.13 installed at " + java_home)
            return java_home

        raise ConanInvalidConfiguration(
            "Failed to find or install bishengjdk 17.0.13. "
            "Set JAVA_HOME or install via: "
            "curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs"
            "/releases/download/pkgs/install-jdk.sh | sh -s -- 17.0.13"
        )

    def _find_sources(self, root):
        files = []
        for dirpath, _dirnames, filenames in os.walk(root):
            for f in filenames:
                if f.endswith(".java"):
                    files.append(os.path.join(dirpath, f))
        return files

    def build(self):
        # 零补丁时为 no-op，与 jackson-core 一致（conan-verify G1 静态门禁要求保留）
        apply_conandata_patches(self)

        java_home = self._ensure_java()
        javac = os.path.join(java_home, "bin", "javac")
        java = os.path.join(java_home, "bin", "java")
        jar = os.path.join(java_home, "bin", "jar")

        src_dir = self.source_folder
        work = os.path.join(self.build_folder, "work")
        classes = os.path.join(work, "classes")
        test_classes = os.path.join(work, "test-classes")
        os.makedirs(classes, exist_ok=True)
        os.makedirs(test_classes, exist_ok=True)

        # 0. 下载编译期 optional 日志适配层（上游 POM <optional>，产物运行时零依赖）
        dep_jars = []
        for key in ("slf4j-api", "commons-logging", "log4j-api"):
            jar_path = os.path.join(work, key + ".jar")
            download(self, filename=jar_path, **self.conan_data[key])
            dep_jars.append(jar_path)
        deps_cp = os.pathsep.join(dep_jars)

        # 1. 编译主源码（sources jar 的 net/htmlparser/jericho/**）
        #    上游 POM 指定 source/target 1.7；JDK 17 支持 -source/-target 7（过时警告）
        main_sources = self._find_sources(os.path.join(src_dir, "net"))
        self.run(
            f'"{javac}" -source 7 -target 7 -nowarn -encoding Cp1252 '
            f'-cp "{deps_cp}" '
            f'-d "{classes}" ' + " ".join(f'"{s}"' for s in main_sources)
        )

        # 2. 打出 JAR
        self.run(
            f'"{jar}" cf "{os.path.join(work, "jericho-html-3.4.jar")}" -C "{classes}" .'
        )

        # 3. 下载 JUnit 4.8.2（上游 test.bat 使用版本）并编译上游测试
        junit_jar = os.path.join(work, "junit-4.8.2.jar")
        download(self, filename=junit_jar, **self.conan_data["junit"])
        tests_root = os.path.join(src_dir, "upstream-tests")
        test_sources = self._find_sources(tests_root)
        # StAXTest 上游整类注释（需 JDK 1.6 StAX），编译排除
        test_sources = [s for s in test_sources if os.path.basename(s) != "StAXTest.java"]
        self.run(
            f'"{javac}" -source 7 -target 7 -nowarn -encoding Cp1252 '
            f'-cp "{classes}{os.pathsep}{junit_jar}" -d "{test_classes}" '
            + " ".join(f'"{s}"' for s in test_sources)
        )

        # 4. 运行上游 JUnit 测试套件（50 个可运行 @Test 方法）
        #    R34/L1c: build() 必须包含上游测试执行
        #    部分用例以相对路径 test/data/*.html 读取数据文件，须在该布局下运行
        run_dir = os.path.join(work, "test-run")
        data_dir = os.path.join(run_dir, "test", "data")
        os.makedirs(data_dir, exist_ok=True)
        for f in os.listdir(os.path.join(tests_root, "data")):
            shutil.copy2(os.path.join(tests_root, "data", f), data_dir)
        run_cp = os.pathsep.join([test_classes, classes, junit_jar])
        self.run(
            f'bash -c "cd \\"{run_dir}\\" && \\"{java}\\" -cp \\"{run_cp}\\" '
            f'org.junit.runner.JUnitCore TestSuite"'
        )

    def package(self):
        jar_path = os.path.join(self.build_folder, "work", "jericho-html-3.4.jar")
        if os.path.exists(jar_path):
            copy(self, "jericho-html-3.4.jar",
                 os.path.join(self.build_folder, "work"),
                 os.path.join(self.package_folder, "libexec"))
        else:
            raise ConanInvalidConfiguration(
                f"Build artifact not found: {jar_path}. "
                "Ensure javac/jar build completed successfully."
            )

        copy(self, "*",
             os.path.join(self.source_folder, "license"),
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # Java 包：产物为 libexec/*.jar，无 native libs，豁免 cpp_info.libs
        self.cpp_info.libdirs = ["libexec"]
