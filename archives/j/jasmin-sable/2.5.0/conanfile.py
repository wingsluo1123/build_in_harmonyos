#!/usr/bin/env python3
"""jasmin-sable 2.5.0 — Jasmin（Java 字节码汇编器，GPL-2.0+）。

上游是 Jasmin：把 `.j`/`.jas` 汇编文本编译成 `.class`。仓库布局：
  * `src/jasmin/`        —— 汇编器本体（主类 **`jasmin.Main`**），`parser.cup` + **已生成**的
                            `parser.java`/`sym.java`（因此**不需要重跑 java_cup 生成**）
  * `lib/jas/src/**`     —— 同包内附带的 “jas” 字节码库（`import jas.*` 被汇编器使用）
  * `generated/scm/**`   —— scm 相关自动生成类（**已随 tarball 提供**，无需跑 autogen 流程）
  * `bin/jasmin`         —— `java jasmin.Main $*` 包装脚本；`build.xml` 是 ant 构建

依赖：源码**直接 `import java_cup.*` / `java_cup.runtime.*`** → java-cup 的 jar 在**编译期与运行期**
都必需；制品仓没有 java-cup → 按“构建/测试期依赖自取”口径从 Maven Central 取（钉 sha256），
并**随包提供**（否则 `jasmin` 跑不起来）。

构建：环境无 ant（也不需要）→ 直接用 JDK 的 `javac` + `jar` 编译上述三处源码，
classpath 加 java-cup；产物 `libexec/jasmin-sable-2.5.0.jar` + `libexec/java-cup-*.jar` +
`bin/jasmin`（包装脚本，自带 classpath）。

上游测试：包内**无测试套件**（`*Test*.java` 为空；`lib/jas/tests/all.java` 是示例）→
上游通过率记 N/A（如实披露）；验证由 test_package 承担（**真跑**：汇编一段 .jas 并执行生成的类）。
"""
import os
import shutil
import stat

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import download, get
from conan.tools.layout import basic_layout

JAR_NAME = "jasmin-sable-2.5.0.jar"
CUP_JAR = "java-cup-11b-20160615-3.jar"
MAIN_CLASS = "jasmin.Main"
SRC_SETS = ("src", "lib/jas/src", "generated")   # 相对源码根
JAVA_CANDIDATES = ("$JAVA_HOME", "~/bishengjdk17", "~/usr/local/bishengjdk17")


class JasminSableConan(ConanFile):
    name = "jasmin-sable"
    version = "2.5.0"
    description = ("Jasmin — Java bytecode assembler (assembles .j/.jas into .class); "
                   "requires the java-cup runtime at run time")
    license = "GPL-2.0-or-later"        # debian/copyright: GPL-2+
    homepage = "https://github.com/Sable/soot/tree/develop/jasmin"   # 上游由 Sable 维护
    url = "https://github.com/Sable/soot/tree/develop/jasmin"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    # ── 工具链 ──────────────────────────────────────────────────────
    # ⚠️ CI Worker **不预装 JDK**（实测构建 #97007：`Invalid configuration: 未找到 JDK（javac）`）。
    #    这里沿用本仓库 Java 配方的既有范式（见 archives/a/aladin、archives/x/xom）：
    #    ① 放宽候选（含 ~/usr/local 下的**嵌套解压目录**、/data/service/hnp/bishengjdk17）；
    #    ② 再看 PATH 上的 javac；
    #    ③ 都没有就用 conan 的 downloader 取 cmd-pkgs 发布的 BiShengJDK 17（走 CI 镜像，不依赖 curl）。
    BISHENGJDK_VERSION = "17.0.13"

    @staticmethod
    def _is_jdk(java_home):
        return all(os.path.isfile(os.path.join(java_home, "bin", tool))
                   for tool in ("java", "javac", "jar"))

    @classmethod
    def _find_jdk_root(cls, base_dir):
        candidates = [base_dir]
        try:
            candidates.extend(os.path.join(base_dir, entry) for entry in sorted(os.listdir(base_dir))
                              if os.path.isdir(os.path.join(base_dir, entry)))
        except OSError:
            pass
        return next((c for c in candidates if cls._is_jdk(c)), None)

    def _java_home(self):
        for cand in (os.environ.get("JAVA_HOME", ""),
                     os.path.expanduser("~/bishengjdk17"),
                     os.path.expanduser("~/usr/local"),
                     os.path.expanduser("~/usr/local/bishengjdk17"),
                     "/storage/Users/currentUser/bishengjdk17",
                     "/storage/Users/currentUser/usr/local",
                     "/usr/local/bishengjdk17",
                     "/usr/local",
                     "/data/service/hnp/bishengjdk17"):
            if cand and self._is_jdk(cand):
                return cand
        javac = shutil.which("javac")
        if javac:
            resolved = os.path.dirname(os.path.dirname(os.path.realpath(javac)))
            if self._is_jdk(resolved):
                return resolved
        # ③ 兜底：用 conan downloader 取 BiShengJDK 17（CI 镜像可用；与 aladin/xom 一致）
        download_dir = os.path.join(self.build_folder, "bishengjdk17")
        resolved = self._find_jdk_root(download_dir)
        if resolved:
            return resolved
        os.makedirs(download_dir, exist_ok=True)
        get(self,
            url=("https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/"
                 "download/pkgs/bishengjdk-%s-ohos-aarch64.tar.gz" % self.BISHENGJDK_VERSION),
            destination=download_dir)
        resolved = self._find_jdk_root(download_dir)
        if resolved:
            return resolved
        raise ConanInvalidConfiguration(
            "未找到 JDK：候选路径与 PATH 均无 java/javac/jar，且从 cmd-pkgs 下载 BiShengJDK %s 后仍无法定位。"
            "请设置 JAVA_HOME（或检查 bishengjdk 包布局）" % self.BISHENGJDK_VERSION)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _fetch_cup(self):
        spec = self.conan_data["build_time_jars"][0]
        dest = os.path.join(self.build_folder, spec["filename"])
        download(self, spec["url"], dest, sha256=spec["sha256"])
        if not os.path.isfile(dest):
            raise ConanInvalidConfiguration("java-cup jar 未就位：%s" % dest)
        return dest

    def build(self):
        javac = os.path.join(self._java_home(), "bin", "javac")
        jar = os.path.join(self._java_home(), "bin", "jar")
        cup = self._fetch_cup()

        sources = []
        for rel in SRC_SETS:
            base = os.path.join(self.source_folder, *rel.split("/"))
            if not os.path.isdir(base):
                raise ConanInvalidConfiguration("缺少源码目录：%s" % rel)
            for root, _dirs, files in os.walk(base):
                sources += [os.path.join(root, f) for f in files if f.endswith(".java")]
        if not sources:
            raise ConanInvalidConfiguration("未找到 Java 源码")

        classes = os.path.join(self.build_folder, "classes")
        os.makedirs(classes, exist_ok=True)
        # 老 Java 源码是 ISO-8859-1（Latin-1）编码：实测有两处字节 0xA4，用 UTF-8 编译会报
        # `unmappable character (0xA4) for encoding UTF-8` → 必须按 Latin-1 编译
        # （与 javac 的默认平台编码一致；上游 build.xml 未指定 encoding）
        self.run('"%s" -nowarn -encoding ISO-8859-1 -cp "%s" -d "%s" %s'
                 % (javac, cup, classes, " ".join('"%s"' % s for s in sources)))
        built = os.path.join(self.build_folder, JAR_NAME)
        self.run('"%s" cf "%s" -C "%s" .' % (jar, built, classes))
        if not os.path.isfile(os.path.join(classes, "jasmin", "Main.class")):
            raise ConanInvalidConfiguration("编译产物缺少 jasmin/Main.class")
        self.output.info("[build] 编译 %d 个 .java（src + lib/jas/src + generated）→ %s"
                         % (len(sources), JAR_NAME))

    def package(self):
        libexec = os.path.join(self.package_folder, "libexec")
        os.makedirs(libexec, exist_ok=True)
        shutil.copyfile(os.path.join(self.build_folder, JAR_NAME),
                        os.path.join(libexec, JAR_NAME))
        # java-cup 是**运行期**依赖：随包提供，否则 jasmin 无法运行
        shutil.copyfile(self._fetch_cup(), os.path.join(libexec, CUP_JAR))

        launcher = os.path.join(self.package_folder, "bin", "jasmin")
        os.makedirs(os.path.dirname(launcher), exist_ok=True)
        with open(launcher, "w") as fh:
            # 注意：classpath 的**每个**条目都要带 $libexec/ 前缀。
            # 实测漏写第二项前缀（只剩文件名）会让 JVM 找不到 java-cup 的运行时类，
            # 端到端运行时表现为 `NoClassDefFoundError: java_cup/runtime/Scanner`。
            fh.write("#!/bin/sh\n"
                     "set -eu\n"
                     "here=$(CDPATH= cd -- \"$(dirname -- \"$0\")\" && pwd)\n"
                     "libexec=\"$here/../libexec\"\n"
                     "exec java -cp \"$libexec/%s:$libexec/%s\" %s \"$@\"\n"
                     % (JAR_NAME, CUP_JAR, MAIN_CLASS))
        os.chmod(launcher, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP
                 | stat.S_IROTH | stat.S_IXOTH)

        for name in ("license.html", "README", "changes"):
            path = os.path.join(self.source_folder, name)
            if os.path.isfile(path):
                shutil.copyfile(path, os.path.join(self.package_folder, name))

    def package_info(self):
        # 可执行 = bin/ 下的包装脚本；jar 放 libexec/
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["libexec"]
        self.cpp_info.libs = []
