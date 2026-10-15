#!/usr/bin/env python3
"""Conan recipe — Apache JMeter 2.13 (pure Java load-testing tool, source compilation).

Downloads the official Apache source archive and builds with Ant:
  ant download_jars package
`download_jars` fetches the pinned third-party runtime jars from Maven Central
(repo1.maven.org; build.properties pins MD5 per jar). `package` compiles all
modules and assembles the runnable distribution layout (bin/ + lib/ + lib/ext/).

Source: https://archive.apache.org/dist/jmeter/source/apache-jmeter-2.13_src.tgz
License: Apache-2.0
Build system: Ant 1.10.15 (binary fetched from archive.apache.org, sha256-pinned;
              upstream ships no ant wrapper). JDK 17 javac no longer accepts
              -source/-target 1.6, so both are overridden to 1.8 on the command
              line (build.xml properties src.java.version/target.java.version;
              no patch needed for that).
Upstream tests: JMeter has an official JUnit suite (`ant test-headless` via
                org.apache.jorphan.test.AllTests) plus batchtests. These are run
                out-of-band as a separate verification step (not inside conan
                build()) to keep the authoritative CI bounded; results are
                recorded honestly in manifest.yaml/notes.md. Consumer
                verification inside CI is provided by test_package/.

R32: validate() checks settings.os in (Linux, OHOS)
R34: test_package/ runs the packaged JMeter binary (--version) + a Java
     consumer program on-device
R38: library-style package (jars under libexec/, no commands.json needed)
"""
import hashlib
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get

ANT_VERSION = "1.10.15"
ANT_URL = ("https://archive.apache.org/dist/ant/binaries/"
           f"apache-ant-{ANT_VERSION}-bin.tar.gz")
ANT_SHA256 = "71334d7e5d98cfe53d6c429a648a5021137a967378667306c5f613dff5180506"

ACTIVATION_VERSION = "1.1.1"
ACTIVATION_URL = ("https://repo1.maven.org/maven2/javax/activation/activation/"
                  f"{ACTIVATION_VERSION}/activation-{ACTIVATION_VERSION}.jar")
ACTIVATION_SHA256 = "ae475120e9fcd99b4b00b38329bd61cdc5eb754eee03fe66c01f50e137724f99"


class JakartaJMeterConan(ConanFile):
    name = "jakarta-jmeter"
    version = "2.13"
    description = ("Apache JMeter 2.13 load and performance testing tool "
                   "(HTTP/JDBC/JMS/FTP/LDAP samplers, headless CLI runner)")
    license = "Apache-2.0"
    homepage = "https://jmeter.apache.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # R32/L0p：四项齐全（Java 包不消费 compiler/build_type，仅进 package_id）
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        pass

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"jakarta-jmeter does not support OS: {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _ensure_java(self):
        """Find bishengjdk 17 in the environment, or auto-install via cmd-pkgs.
        (same logic as archives/j/jakarta-activation 2.0.0)

        注意：HNP 自带的 /data/service/hnp/bin/java 在部分环境下无法启动
        （VM init 失败），故优先 JAVA_HOME 与 ~/bishengjdk17（cmd-pkgs 安装）。"""
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
        install_url = ("https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs"
                       "/releases/download/pkgs/install-jdk.sh")
        script_path = os.path.join(os.path.expanduser("~"), ".install-jdk.sh")
        self.run('curl -fsSL -o "{}" "{}"'.format(script_path, install_url))
        self.run('sh "{}" 17.0.13'.format(script_path))
        java_home = os.path.expanduser("~/bishengjdk17")
        if os.path.isfile(os.path.join(java_home, "bin", "java")):
            self.output.info("bishengjdk 17.0.13 installed at " + java_home)
            return java_home
        raise ConanInvalidConfiguration(
            "Failed to find or install bishengjdk 17.0.13. Set JAVA_HOME or install via: "
            "curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs"
            "/releases/download/pkgs/install-jdk.sh | sh -s -- 17.0.13"
        )

    def _ensure_ant(self):
        """Fetch Apache Ant binary tarball from archive.apache.org (sha256-pinned).
        Upstream ships no ant wrapper. Cached under ~/apache-ant-<ver>."""
        ant_home = os.path.expanduser("~/apache-ant-" + ANT_VERSION)
        ant_sh = os.path.join(ant_home, "bin", "ant")
        if os.path.isfile(ant_sh):
            self.output.info("Ant found at " + ant_home)
            return ant_home
        self.output.info("Ant not found — downloading apache-ant-" + ANT_VERSION + " ...")
        dest = os.path.expanduser("~/apache-ant-" + ANT_VERSION + "-bin.tar.gz")
        try:
            self.run('curl -fsSL --retry 3 --connect-timeout 30 -o "{}" "{}"'.format(dest, ANT_URL))
        except ConanException:
            # OHOS 真机无 curl、python3 无 CA bundle：urllib 免证书下载，
            # 完整性由下方 sha256 钉校验兜底
            self.output.warning("curl unavailable/failed — python3 urllib fallback (no TLS verify; sha256 pin below)")
            py = (
                "import ssl,urllib.request,shutil;"
                "ctx=ssl._create_unverified_context();"
                "o=urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx));"
                "r=o.open('{}',timeout=300);f=open('{}','wb');"
                "shutil.copyfileobj(r,f);f.close();r.close()"
            ).format(ANT_URL, dest)
            self.run('python3 -c "{}"'.format(py))
        h = hashlib.sha256()
        with open(dest, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        if h.hexdigest() != ANT_SHA256:
            raise ConanInvalidConfiguration(
                "apache-ant tarball sha256 mismatch: " + h.hexdigest()
            )
        os.makedirs(ant_home, exist_ok=True)
        self.run('tar -xzf "{}" -C "{}" --strip-components=1'.format(dest, ant_home))
        if not os.path.isfile(ant_sh):
            raise ConanInvalidConfiguration("Ant extraction failed: " + ant_sh)
        self.output.info("Ant installed at " + ant_home)
        return ant_home

    def _ensure_activation_jar(self):
        """Fetch javax.activation:activation jar from repo1.maven.org (sha256-pinned)
        into the source tree lib/.

        javax.activation 曾随 JDK 提供（JDK 11 起摘除）；JMeter 2.13 的 SMTP 采样器
        编译期需要该包——jm-0002 补丁已把 lib/activation-1.1.1.jar 加入 build.xml
        classpath，本方法负责取 jar，package() 随 lib/*.jar 打包进产物
        （NewDriver 运行时全量装载 lib/*.jar）。"""
        dest = os.path.join(self.source_folder, "lib", "activation-1.1.1.jar")
        if os.path.isfile(dest) and os.path.getsize(dest) > 60000:
            self.output.info("activation jar already present at " + dest)
            return
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        try:
            self.run('curl -fsSL --retry 3 --connect-timeout 30 -o "{}" "{}"'.format(dest, ACTIVATION_URL))
        except ConanException:
            # OHOS 真机无 curl、python3 无 CA bundle：urllib 免证书下载，
            # 完整性由下方 sha256 钉校验兜底
            self.output.warning("curl unavailable/failed — python3 urllib fallback (no TLS verify; sha256 pin below)")
            py = (
                "import ssl,urllib.request,shutil;"
                "ctx=ssl._create_unverified_context();"
                "o=urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx));"
                "r=o.open('{}',timeout=300);f=open('{}','wb');"
                "shutil.copyfileobj(r,f);f.close();r.close()"
            ).format(ACTIVATION_URL, dest)
            self.run('python3 -c "{}"'.format(py))
        h = hashlib.sha256()
        with open(dest, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        if h.hexdigest() != ACTIVATION_SHA256:
            raise ConanInvalidConfiguration(
                "activation jar sha256 mismatch: " + h.hexdigest()
            )
        self.output.info("activation-1.1.1.jar fetched (sha256 ok) at " + dest)

    def build(self):
        apply_conandata_patches(self)
        java_home = self._ensure_java()
        ant_home = self._ensure_ant()
        self._ensure_activation_jar()
        os.environ["JAVA_HOME"] = java_home
        os.environ["PATH"] = (os.path.join(java_home, "bin") + ":" +
                              os.environ.get("PATH", ""))
        # JDK 17 javac 已移除 -source/-target 1.6（build.xml 默认值），
        # 用命令行属性覆盖（Ant 命令行 -D 优先级高于 build.xml <property>）
        # download_jars: 从 Maven Central 拉取 build.properties 钉 MD5 的运行时 jar
        # package: 编译全部模块并组装 bin/ + lib/ + lib/ext/ 可运行布局
        self.run(
            f'bash -c "cd {self.source_folder} && sh {ant_home}/bin/ant '
            f'-Dsrc.java.version=1.8 -Dtarget.java.version=1.8 download_jars package"',
            env="conanbuild",
        )

    def package(self):
        # 组装可运行的 JMeter home 布局（bin/ApacheJMeter.jar + lib/ + lib/ext/）。
        # NewDriver 以自身 jar 位置推断 jmeter.home 并按 ../lib、../lib/ext 装载 jar。
        # 注意：conan.tools.files.copy 会保留 pattern 之前的目录层级——
        # 故以各子目录为 src、裸文件名通配做 pattern，保证平铺落到目标目录。
        src = self.source_folder
        jmeter_home = os.path.join(self.package_folder, "libexec", "jmeter")
        bin_src = os.path.join(src, "bin")
        bin_dst = os.path.join(jmeter_home, "bin")
        # bin/: 主 jar + 运行时配置（排除启动脚本/testfiles/examples/templates）
        copy(self, "ApacheJMeter.jar", bin_src, bin_dst)
        for pattern in ("*.properties", "*.conf", "*.xml",
                        "*.parameters", "*.bshrc"):
            copy(self, pattern, bin_src, bin_dst)
        # lib/: 第三方运行时 jar（download_jars 产物 + activation-1.1.1.jar）
        copy(self, "*.jar", os.path.join(src, "lib"),
             os.path.join(jmeter_home, "lib"))
        # lib/ext/: ApacheJMeter_* 模块 jar
        copy(self, "ApacheJMeter_*.jar", os.path.join(src, "lib", "ext"),
             os.path.join(jmeter_home, "lib", "ext"))
        # 许可与文档
        copy(self, "LICENSE", src, jmeter_home)
        copy(self, "NOTICE", src, jmeter_home)
        copy(self, "README", src, jmeter_home)
        copy(self, "*", os.path.join(src, "licenses"),
             os.path.join(jmeter_home, "licenses"))

    def package_info(self):
        self.cpp_info.libdirs = ["libexec"]
