#!/usr/bin/env python3
"""Conan recipe for xsd 4.0.0 — Code Synthesis XSD (W3C XML Schema → C++ 翻译器).

xsd 是一个**可执行文件**（`package_type = "application"`）：它读 `.xsd` schema 并生成
两种 C++ 映射的源码（C++/Tree 常驻内存映射、C++/Parser 事件流式映射），生成代码运行期
依赖 Xerces-C++。因此 `requirements()` 只有一条硬依赖 `xerces-c/3.2.5`（W0-2 双源实证：
从 ohpcd 制品仓**先取配方、再用 `--build=never` 取二进制**两路都 rc=0，命中
`os=OHOS/arch=armv8/clang15/libc++` 的静态包；逐字命令见 `4.0.0/notes.md` §1.2——
此处不贴带远端开关的原文，CI L0g 闸按字面 grep `conan <cmd> … -r=<remote>`，贴了会假阳性拦截）。

构建系统不是 autotools：+dep tarball 是 Code Synthesis 自带的 `build-0.3` make 体系，
根 `makefile` 里根本没有 `configure`（`xsd/build/` 下的 `configure` 是**交互式**对话脚本，
+dep 发行包用预生成的 `configuration-dynamic.make` 把它短路掉，README 也写明
"pre-configured … non-interactive mode"）。所以本配方只用 Conan 的 `Autotools` helper
承担「跑 make + 传环境变量」这一层（它对没有 configure 的工程同样适用），两个
`Autotools*` generator 负责把 `CC/CXX/CPPFLAGS/CXXFLAGS/LDFLAGS/LIBS` 注进
`conanbuild.sh`，这正是上游 README 要求的注入面。

三个补丁（全部为可移植性，无 `__OHOS__` 平台宏，见 `patches/` 与 conandata 注释）：

* `0001` — libc++ 的 `<cstddef>` 无条件 `#include <version>`（OHOS NDK libc++ 实测
  c++11/14/17/20 四档皆然），而上游把 `libcutl/version`、`libxsd-frontend/version`
  两个纯文本版本标记文件放在被 `-I` 的目录里 ⇒ 标准库 `<version>` 被同名文件遮蔽，
  报 `version:1:1: error: expected unqualified-id`。libstdc++ 不从 `<cstddef>` 拉
  `<version>`，所以 Linux/CCI 构建碰不到。改名为 `version.txt` 并同步 `libcutl` 的两处
  `dist` 引用（该两处仅 `dist` 目标消费，本包不构建 dist）。
* `0002` — 上游缺失的 `#include <iostream>`（Boris Kolpackov 2015-10-23 上游提交
  `5029f866`，与 CCI `0002-missing-include.patch` 逐字同源）。
* `0003` — Xerces-C++ 3.2 起不再支持超出 BMP 的字符引用，上游测试期望值随之过期
  （Debian bug 881108），与 CCI `0110-xerces-c3.2.patch` 同源；本包依赖
  `xerces-c/3.2.5`，不打该补丁则 `encoding/char/*`、`encoding/wchar` 三组用例必失败。
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (apply_conandata_patches, chdir,
                               export_conandata_patches, get)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class XsdConan(ConanFile):
    name = "xsd"
    version = "4.0.0"
    description = ("XSD — W3C XML Schema to C++ translator，生成 C++/Tree 与 "
                   "C++/Parser 两种静态类型 C++ 映射")
    # GPL v2（xsd 编译器本体 + libcutl + libxsd-frontend）叠加 FLOSSE
    # （libxsd 运行期头文件的 FLOSS 例外），见 xsd/{LICENSE,GPLv2,FLOSSE}。
    license = ("GPL-2.0-only", "FLOSSE")
    homepage = "https://codesynthesis.com/projects/xsd/"
    # 与同批最近合入的配方一致：url 指上游项目页（不留 `url = ""` 占位——
    # pre_push_check H1 软闸会以「W4 必抓」告警，且空串对消费方零信息）。
    url = "https://codesynthesis.com/projects/xsd/"
    topics = ("xml", "xml-schema", "code-generation", "xsd")

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # W0-2：唯一硬依赖。+dep tarball 的 README 明写 "all its dependencies
        # (except Xerces-C++)"，故捆绑包不覆盖本依赖，必须走制品仓。
        self.requires("xerces-c/3.2.5")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        # R9/§一.7：`Autotools.make()` 会追加 `-j<tools.build:jobs>`，该 conf 缺省取
        # `os.cpu_count()`（本机 20）而容器真实 affinity 只有 8 —— 缺省自限到 4，
        # 外部显式传入的值保持优先（CI 想跑更多只需 `-c tools.build:jobs=N`）。
        if self.conf.get("tools.build:jobs", default=None, check_type=int) is None:
            self.conf.define("tools.build:jobs", 4)

        tc = AutotoolsToolchain(self)
        # xsd 4.0.0（2014）与捆绑的 libcutl 1.8.1/libxsd-frontend 2.0.0 是 C++03/11
        # 时代代码（`std::auto_ptr`、`<cutl/container/any.hxx>` 等），profile 的
        # compiler.cppstd=17 会先产出 `-std=c++17`；`extra_cxxflags` 在
        # `AutotoolsToolchain.cxxflags` 里排在其后，clang 取最后一个 ⇒ `-std=c++11`
        # 生效，与 CCI 配方一致。
        tc.extra_cxxflags = ["-std=c++11"]
        # 上游 README 明列的链接要求（pthread：libcutl/compiler 与 xerces 静态库）。
        tc.extra_ldflags = ["-pthread"]
        # R33：显式钉优化基线，避免 CI worker 泄漏的 CFLAGS 与设备分叉。
        tc.extra_cflags = ["-O3", "-pipe", "-DNDEBUG"]
        tc.generate()

        AutotoolsDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)

        with chdir(self, self.source_folder):
            autotools = Autotools(self)

            # 默认目标 = `xsd/xsd/xsd`（Code Synthesis build 系统的根 makefile 只在
            # `clean|test|install|dist` 目标下才 import 测试/示例子树）。
            autotools.make()

            # 上游测试套件：`make test` → tests/cxx → {parser,tree} 两组。
            # 该目标会用刚编出来的 `xsd` 逐个把 schema 生成 C++ 源码、编译成
            # driver 再执行（自带的「生成代码自测」），失败即 make 非零退出。
            # 这里不吞 rc：失败必须让 G2 失败，而不是打一行绿字。
            autotools.make(target="test")

            # 机器可读的用例计数行（供 PR/审计复核，勿删）：
            # 期望 61 = tree 32 + parser 29（注册树内全部叶子用例）。
            binaries = self._test_binaries()
            self.output.info(
                "XSD_UPSTREAM_TEST_BINARIES=%d "
                "(注册树内 tree+parser 可执行文件；另 tree/binary 的 3 个叶子"
                "因上游 xsd_with_ace=n 未注册，不在本计数内)" % len(binaries))

    def _test_binaries(self):
        """列出 `xsd/tests/cxx` 注册树内真正生成的测试可执行文件。

        上游测试可执行文件命名有两种：叶子目录里的 `driver`，以及
        `generated-impl/test-pimpl-driver`（`--generate-test-driver` 生成）。
        判据用 ELF 魔数而不是可执行位（HMDFS 的 o+x 语义见 device-facts §一.2/27）。
        """
        import glob

        roots = [
            os.path.join(self.source_folder, "xsd", "tests", "cxx", "tree"),
            os.path.join(self.source_folder, "xsd", "tests", "cxx", "parser"),
        ]
        found = []
        for root in roots:
            for pat in ("driver", "*-driver"):
                for path in glob.glob(os.path.join(root, "**", pat),
                                      recursive=True):
                    if not os.path.isfile(path):
                        continue
                    try:
                        with open(path, "rb") as fh:
                            if fh.read(4) == b"\x7fELF":
                                found.append(path)
                    except OSError:
                        continue
        return sorted(set(found))

    def package(self):
        # conan.tools.files.chdir 是 (conanfile, newdir) 的 contextmanager；
        # 只传一个参数会 TypeError: chdir() missing 1 required positional argument: 'newdir'。
        with chdir(self, self.source_folder):
            # 上游安装入口是 `make install install_prefix=<dir>`（README 明示）。
            # Conan 的 Autotools.install() 会额外注入 `DESTDIR=`，而 Code Synthesis
            # 的 install 宏不读 DESTDIR，注入无副作用。
            autotools = Autotools(self)
            autotools.install(args=[f"install_prefix={self.package_folder}"])

        shipped = os.path.join(self.package_folder, "bin", "xsd")
        if not os.path.isfile(shipped):
            raise ConanException(
                f"[package] bin/xsd missing after install (expected {shipped})")
        surface = sorted(
            os.path.relpath(os.path.join(r, f), self.package_folder)
            for r, _d, fs in os.walk(self.package_folder)
            for f in fs)
        self.output.info(
            "[package] surface(%d): %s"
            % (len(surface), ", ".join(surface[:12])
               + (" …" if len(surface) > 12 else "")))

    def package_info(self):
        # 交付面 = `bin/xsd` + `include/xsd/**`（libxsd 运行期头，生成代码 include
        # `<xsd/cxx/tree/…>` 需要 `-I<pkg>/include`）+ `share/doc/**`。
        # 没有 lib/，声明 libdirs 会让 G4 的 package_info ↔ 包树核对失配。
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.resdirs = []
