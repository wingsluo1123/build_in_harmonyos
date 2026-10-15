#!/usr/bin/env python3
"""Conan recipe — keycloak-config-cli 6.4.0 (Keycloak config import CLI).

Upstream: adorsys/keycloak-config-cli (tag v6.4.0, v-prefixed, Apache-2.0)
Spring Boot 3.2.9 CLI that imports JSON/YAML-formatted realm configuration
into Keycloak via the Keycloak admin REST API.

Package layout (follows archives/j/jackson-core/2.14.1 precedent):
  libexec/keycloak-config-cli.jar   <- fat jar (spring-boot-maven-plugin,
                                       layout=ZIP; finalName without version)
  licenses/LICENSE.txt

Build chain:
  bishengjdk 17.0.13 (auto-install via cmd-pkgs, same chain as
  jackson-core 2.14.1 / keycloak-metrics 7.0.0)
  + Maven 3.9.6 via the upstream-committed ./mvnw wrapper
    (.mvn/wrapper/maven-wrapper.jar is committed; distributionUrl points at
    repo.maven.apache.org)
  + Maven Central dependencies — compiled and bundled into the fat jar
    (runtime artifact is self-contained, zero external runtime deps)

JDK: upstream CI build-pom-version job matrix [17, 21] proves the project
builds with -Djava.version=17 — we build with 17 to match bishengjdk17.

Upstream tests: 490 @Test methods in 72 test files (JUnit 5).
  - surefire unit tests: run in build() (upstream test execution, R34)
  - failsafe *IT integration tests (41 files): testcontainers-based, require
    a Docker daemon — unavailable on this platform, skipped with -DskipITs
    and documented in notes.md with the concrete technical reason (R51)

R32: validate() checks settings.os in (Linux, OHOS)
R34: build() runs upstream unit tests; test_package executes the real CLI
R38: CLI tool package — software-level commands.json required
"""
import glob
import os
import shutil
import stat

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class KeycloakConfigCliConan(ConanFile):
    name = "keycloak-config-cli"
    version = "6.4.0"
    description = (
        "Keycloak Configuration CLI — imports JSON/YAML-formatted realm "
        "configuration into Keycloak via the admin REST API"
    )
    license = "Apache-2.0"
    homepage = "https://github.com/adorsys/keycloak-config-cli"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"  # CLI 工具（R38/code-style §2；PF8 CLI 分类依据）

    # L0 质量门禁要求 settings 全四项（keycloak-metrics/graalvm 先例同款）；
    # 纯 Java 包不实际消费 compiler/build_type，仅满足门禁与 profile 完整性
    settings = "os", "compiler", "build_type", "arch"

    # pom.xml: <finalName>${project.artifactId}</finalName> → 无版本号
    _jar_name = "keycloak-config-cli.jar"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        pass

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"keycloak-config-cli does not support OS: {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _ensure_java(self):
        """Find bishengjdk 17 in the environment, or auto-install via cmd-pkgs.

        Same chain as archives/j/jackson-core/2.14.1:
          1. JAVA_HOME environment variable
          2. ~/bishengjdk17 and ~/usr/local/bishengjdk17 (standard cmd-pkgs paths)
          3. java on PATH
          4. Auto-install via cmd-pkgs install-jdk.sh 17.0.13 (CI workers may lack JDK)

        Returns the JAVA_HOME path. Raises ConanInvalidConfiguration if all fail.
        """
        # 1. Check JAVA_HOME env
        java_home = os.environ.get("JAVA_HOME", "")
        if java_home and os.path.isfile(os.path.join(java_home, "bin", "java")):
            self.output.info("Java found via JAVA_HOME=" + java_home)
            return java_home

        # 2. Check common cmd-pkgs install locations
        for candidate in [
            os.path.expanduser("~/bishengjdk17"),
            os.path.expanduser("~/usr/local/bishengjdk17"),
        ]:
            if os.path.isfile(os.path.join(candidate, "bin", "java")):
                self.output.info("Java found at " + candidate)
                return candidate

        # 3. Try to find java in PATH
        java_in_path = shutil.which("java")
        if java_in_path:
            candidate = os.path.dirname(os.path.dirname(os.path.realpath(java_in_path)))
            self.output.info("Java found in PATH at " + candidate)
            return candidate

        # 4. Auto-install bishengjdk 17.0.13 via cmd-pkgs
        self.output.info("Java not found — installing bishengjdk 17.0.13 via cmd-pkgs...")
        install_url = (
            "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs"
            "/releases/download/pkgs/install-jdk.sh"
        )
        script_path = os.path.join(self.source_folder, ".install-jdk.sh")
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

    def build(self):
        # 应用补丁（本包无源码补丁：patches: {}；-Djava.version=17 与
        # -javaagent 均为上游 CI 自身支持的构建参数，非源码修改）
        apply_conandata_patches(self)

        # 确保 JDK 17 可用（CI worker 可能未预装，自动通过 cmd-pkgs 安装）
        java_home = self._ensure_java()
        os.environ["JAVA_HOME"] = java_home
        os.environ["PATH"] = os.path.join(java_home, "bin") + ":" + os.environ.get("PATH", "")

        # 赋予 mvnw 执行权限（upstream tarball 内 mvnw 可能无 x 位）
        mvnw = os.path.join(self.source_folder, "mvnw")
        if os.path.exists(mvnw):
            os.chmod(mvnw, os.stat(mvnw).st_mode | stat.S_IEXEC)

        # 固定 maven 本地仓：OHOS 真机 JVM user.home 异常（落 cwd 下 "?" 目录），
        # 必须显式 pin；固定路径同时供多阶段/多次构建复用缓存
        repo_local = os.path.expanduser("~/.m2/repository")
        common = (
            "-B -ntp -Djava.version=17 "
            f'-Dmaven.repo.local="{repo_local}" '
            # 上游 CI MAVEN_CLI_OPTS 同款重试（本机实测 repo.maven.apache.org
            # 大文件传输偶发 Connection aborted，重试参数消除抖动）
            "-Dmaven.wagon.http.retryHandler.count=5 "
            "-Daether.connector.basic.threads=3 "
        )

        # 阶段 1：依赖解析 + 测试编译（填充本地仓，不执行测试）
        #   -Djava.version=17：上游 CI build-pom-version job 矩阵 [17,21]
        #   证明 17 可完整编译（pom 默认 21，本机 bishengjdk 为 17）
        self.run(
            f'bash -c "cd {self.source_folder} && ./mvnw {common} test-compile"',
            env="conanbuild",
        )

        # 阶段 2：定位 byte-buddy-agent（mockito inline mock maker 的 attach 载体）
        # 根因（本机实测 31/90 用例 ERROR 同因）：OHOS/BiSheng JDK 上 JVM 动态
        # attach 机制不可用（外部 attach 子进程不返回 + 自附加抛异常）→ Mockito 5
        # inline mock maker 初始化失败 → 一切使用 @Mock 的单测报错。
        # 修复（Mockito 官方推荐，keycloak-metrics 7.0.0 同因先例）：-javaagent
        # premain 预注册 Instrumentation，运行时 ByteBuddyAgent 检测到已装载
        # agent 直接短路，零 attach 调用。纯构建参数，零源码修改。
        agent_jar = self._find_newest(repo_local, "byte-buddy-agent-*.jar")
        if not agent_jar:
            raise ConanInvalidConfiguration(
                "byte-buddy-agent jar not found in maven local repository — "
                "cannot pre-register Mockito instrumentation on OHOS"
            )
        self.output.info(f"Mockito instrumentation agent: {agent_jar}")
        argline = (
            "--add-exports=java.base/sun.security.x509=ALL-UNNAMED "
            "--add-exports=java.base/sun.security.util=ALL-UNNAMED "
            f"-javaagent:{agent_jar} "
            "-Djdk.attach.allowAttachSelf=true"
        )

        # 阶段 3：上游测试（surefire 单测）+ 打包（R34）
        #   -DskipITs：failsafe *IT 基于 testcontainers（docker-java 3.4.0），
        #   需 Docker daemon 拉起 Keycloak 容器；本平台无 Docker
        #   （具体技术原因见 notes.md R51 申报表）
        self.run(
            f'bash -c "cd {self.source_folder} && ./mvnw {common} clean verify '
            f'-DskipITs -DargLine=\\"{argline}\\""',
            env="conanbuild",
        )

    def _find_newest(self, root, pattern):
        """在目录树中找 pattern 匹配的最新构件（字典序最大 = 最高版本）。"""
        matches = glob.glob(os.path.join(root, "**", pattern), recursive=True)
        return max(matches) if matches else None

    def package(self):
        # 打包编译产物 fat jar
        jar_path = os.path.join(self.source_folder, "target", self._jar_name)
        if os.path.exists(jar_path):
            copy(self, self._jar_name, os.path.join(self.source_folder, "target"),
                 os.path.join(self.package_folder, "libexec"))
        else:
            raise ConanInvalidConfiguration(
                f"Build artifact not found: {jar_path}. "
                "Ensure Maven build completed successfully."
            )

        # 打包 LICENSE（upstream 文件名为 LICENSE.txt）
        copy(self, "LICENSE.txt", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libdirs = ["libexec"]
