#!/usr/bin/env python3
"""Conan recipe — pkgfile 25（Arch 仓库 .files 元数据搜索工具，Meson + C++20）

pkgfile 读取 alpm `.files` 数据库，反查「某个文件属于哪个软件包」：
`pkgfile -u` 拉取并转换仓库元数据到本地缓存，`pkgfile -s <file>` 按文件反查包，
`pkgfile -l <pkg>` 列出包内文件。上游：https://github.com/falconindy/pkgfile

OHOS 适配要点（完整分析见 notes.md 与 reports/pre-adaptation-analysis.md）：

* **C++20**：上游 meson.build 的 default_options 要求 `cpp_std=c++20`，源码使用
  `std::format`(44 处) / `std::span` / `operator<=>`；CI profile 固定
  `compiler.cppstd=17`，会让 MesonToolchain 注入 `cpp_std=c++17`
  → configure() 内覆盖为 20（apache-arrow/24.0.0 同口径）。
* **libc++ 15 的 `<format>`**：OHOS SDK clang 15 + libc++ 15004 默认不暴露
  `std::format`，须定义 `_LIBCPP_ENABLE_EXPERIMENTAL` 且链接 `libc++experimental.a`
  （asyncpp/0.2.4、libpqxx/8.0.1 同口径）。
* **libsystemd**：上游把 `libsystemd` 写成无条件依赖（`pkgfiled` 守护进程使用
  sd-event/sd-notify）。OHOS 无 systemd，ohpcd 制品仓也无 libsystemd 制品
  （W0：`conan list libsystemd/* -r=ohpcd` = 0 命中）→ 补丁 0001 把守护进程改为
  可关闭，构建时 `-Ddaemon=false`，只构建 pkgfile CLI。
* **pod2man**：上游把 `pod2man` 作为 `find_program` 硬要求；OHOS 无 perl
  → 补丁 0002 改为可关闭，构建时 `-Dman_pages=false`。
* **pkg-config 名**：上游依赖 `libpcre`，而 pcre 配方未声明 `pkg_config_name`，
  PkgConfigDeps 只会生成 `pcre.pc` → 在消费侧用官方支持的
  `PkgConfigDeps.set_property()` 改写为 `libpcre`（不改上游 meson.build）。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class PkgfileConan(ConanFile):
    name = "pkgfile"
    version = "25"
    description = "pkgfile — search for files in Arch repository packages (.files metadata explorer)"
    license = "MIT"
    homepage = "https://github.com/falconindy/pkgfile"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # 产物只有可执行文件（bin/pkgfile），无库/头文件导出
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"run_upstream_tests": [True, False]}
    default_options = {"run_upstream_tests": True}

    # PkgConfigDeps 在 generate() 内手动调用（须先改写 pcre 的 pkg-config 名，
    # 见 generate()），故类级 generators 保持为空。
    generators = []

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        # 上游 meson.build:7 default_options 为 cpp_std=c++20，源码使用
        # std::format / std::span / operator<=>。CI profile 的 compiler.cppstd=17
        # 会被 MesonToolchain 转成 cpp_std=c++17 覆盖项目默认值 → 显式抬到 20。
        self.settings.compiler.cppstd = "20"

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        # 上游 INSTALL 声明的运行期依赖：libcurl / libarchive / pcre / pthreads
        # （pthreads 由 meson 的 dependency('threads') 处理，无需 conan 包）。
        # 版本均为 W0 在 ohpcd 上以 conan download 实证可用的版本。
        self.requires("pcre/8.45")
        self.requires("libarchive/3.8.7")
        self.requires("curl/8.15.0.1")

    def build_requirements(self):
        # meson 配方 requirements() 为 pass（不代管 ninja），二者都要显式声明。
        self.tool_requires("meson/1.11.0")
        self.tool_requires("ninja/1.12.1")
        # 上游 meson.build:41 把 pkg-config 作为 find_program 硬要求；
        # pkgconf 包在 bin/ 提供 pkg-config 别名（ayatana-indicator-keyboard 同款）。
        self.tool_requires("pkgconf/3.0.5")
        if self.options.run_upstream_tests and can_run(self):
            # 上游单测（src/filter_test.cc + src/repo_test.cc）需要 gtest 与 gmock
            # （meson.build:37-38，两者 required: false）。gmock/1.17.0 传递依赖
            # gtest/1.17.0（transitive_headers/libs=True），故只声明 gmock。
            # test_requires 不传播给消费者。
            self.test_requires("gmock/1.17.0")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    @staticmethod
    def _abs_tool(*names):
        """把构建工具解析成**绝对路径**。

        OHOS 上 posix_spawn 不搜索 PATH：meson 在探测静态归档器时用裸名 exec
        `llvm-ar-15`/`llvm-ar`/`ar`/`gar` 会全部报 ENOENT（即使 `ar` 确实在
        PATH 中），错误形如
        `ERROR: Unknown linker(s): [['llvm-ar-15'], ['llvm-ar'], ['ar'], ['gar']]`。
        pkgfile 用 `static_library('pkgfile', ...)` 构建 libcommon.a，因此归档器是
        必需项（appstream/1.2.0、account-utils/1.4.0 同款处置）。
        搜索顺序：PATH → ~/usr/local/bin → /data/service/hnp/bin。
        """
        home_bin = os.path.join(os.path.expanduser("~"), "usr", "local", "bin")
        for name in names:
            for cand in (name,
                         os.path.join(home_bin, name),
                         os.path.join("/data/service/hnp/bin", name)):
                found = shutil.which(cand)
                if found:
                    return found
        return None

    def _pkg_config_binary(self):
        """定位可用的 pkg-config 可执行文件。

        OHOS 无系统 pkg-config；ohpcd 的 pkgconf/3.0.5 包内**只落了 bin/pkgconf**，
        配方里的 pkg-config 别名没有真正生成（真机实测包目录只有 pkgconf），
        因此 meson 的 `find_program('pkg-config')` 与 `dependency('libpcre')` 的
        pkg-config 查找都会失败（`Pkg-config for machine host machine not found`）。
        这里按「PATH → 常见目录 → tool_requires 包内 bin/」的顺序解析绝对路径，
        交给 MesonToolchain 写进 machine file 的 pkgconfig/pkg-config 两项。
        """
        found = self._abs_tool("pkg-config", "pkgconf")
        if found:
            return found
        for attr in ("build", "host"):
            group = getattr(self.dependencies, attr, None)
            if group is None:
                continue
            for dep in list(group.values()):
                if getattr(dep.ref, "name", None) != "pkgconf":
                    continue
                package_folder = dep.package_folder
                if not package_folder:
                    continue
                for binary in ("pkg-config", "pkgconf"):
                    candidate = os.path.join(package_folder, "bin", binary)
                    if os.path.isfile(candidate):
                        return candidate
        return None

    def generate(self):
        tc = MesonToolchain(self)
        # OHOS 无 systemd、无 perl(pod2man)：关闭上游的守护进程与 man 页
        # （两个开关由补丁 0001/0002 引入，默认值 true 保持 Linux 行为不变）。
        # 必须传 Python bool：MesonToolchain.to_meson_value 会把字符串引号化，
        # 传 "false" 会在 machine file 里写成 daemon = 'false'（字符串），
        # meson 对 boolean 选项拒绝字符串值而报错。
        # R32：平台判断使用 in ("Linux", "OHOS")。
        if str(self.settings.os) in ("Linux", "OHOS"):
            tc.project_options["daemon"] = False
            tc.project_options["man_pages"] = False
            # 上游 meson.build:18 用
            #   cpp.get_define('ARCHIVE_FILTER_ZSTD', args: ['-include','archive.h'])
            # 探测 libarchive 头宏，但该探测只带 args、不带 dependency() 的 include
            # 路径；OHOS 上 libarchive 是 conan 包，archive.h 不在系统默认搜索路径，
            # 探测失败会让 configure 直接报
            #   ERROR: Could not get define 'ARCHIVE_FILTER_ZSTD'
            # （上游把该探测写在 dependency('libarchive') 之前，无法就地复用）。
            # 按 appstream/1.2.0 对同类 configure 期探测的处置，把依赖 include 目录
            # 显式补进全局编译参数——与 .pc 提供的 -I 相同，不改变编译语义。
            # 运行期库查找：Conan 的 MesonToolchain 只注入 -Wl,-rpath-link
            # （链接期），不写入运行期 rpath；而 CI 的 L2 smoke test 与
            # conan-verify L2 都是**裸执行** `bin/pkgfile --version`
            # （ci/conan/build_and_test.sh:1680、scripts/ohc/conan_verify.py:816），
            # 不加载 conanrun 环境。本项目依赖里只有 curl 是 shared
            # （libarchive 无 shared 选项=静态，pcre shared=False，
            # curl 自身静态链接 openssl/zlib），故为全部 host 依赖补
            # -L/-Wl,-rpath，使产物脱离 LD_LIBRARY_PATH 也能启动。
            # 这是仓库既有做法（akku/1.1.0、bsdtar/3.7.7 同款）。
            for dep in self.dependencies.filter({"build": False}).values():
                cppinfo = dep.cpp_info.aggregated_components()
                for incdir in cppinfo.includedirs:
                    tc.extra_cxxflags.append(f"-I{incdir}")
                for libdir in cppinfo.libdirs:
                    tc.extra_ldflags.append(f"-L{libdir}")
                    tc.extra_ldflags.append(f"-Wl,-rpath,{libdir}")
            # 上游 meson.build:31/41 依赖 pkg-config（dependency('libpcre') 与
            # find_program('pkg-config') 都是硬要求），OHOS 无系统 pkg-config，
            # 故显式把 machine file 的 pkgconfig/pkg-config 指向 pkgconf 包内
            # 绝对路径（pkgconf 是 pkg-config 的兼容实现）。
            pkg_config = self._pkg_config_binary()
            if pkg_config is None:
                raise ConanInvalidConfiguration(
                    "pkgfile 需要 pkg-config 解析 libpcre/libarchive/libcurl；"
                    "已声明 tool_requires pkgconf/3.0.5 但未找到可执行文件"
                )
            tc.pkgconfig = pkg_config
            # 静态归档器等 binutils 必须是绝对路径（见 _abs_tool 说明）。
            # tc.binaries 的优先级高于 MesonToolchain 自动推导的裸名值。
            archiver = self._abs_tool("llvm-ar", "ar")
            if archiver is None:
                raise ConanInvalidConfiguration(
                    "pkgfile 需要静态归档器 ar/llvm-ar（libcommon.a 为 static_library），"
                    "但 PATH / ~/usr/local/bin / /data/service/hnp/bin 均未找到"
                )
            tc.binaries["ar"] = archiver
            for key, names in (
                ("as", ("llvm-as", "as")),
                ("strip", ("llvm-strip", "strip")),
                ("nm", ("llvm-nm", "nm")),
                ("ranlib", ("llvm-ranlib", "ranlib")),
            ):
                resolved = self._abs_tool(*names)
                if resolved:
                    tc.binaries[key] = resolved
        if str(self.settings.os) == "OHOS":
            # OHOS SDK clang 15 + libc++ 15004：<format> 默认关闭，须
            # _LIBCPP_ENABLE_EXPERIMENTAL 才暴露 std::format，其运行时符号在
            # libc++experimental.a（asyncpp/0.2.4、libpqxx/8.0.1 同口径）。
            tc.extra_defines.append("_LIBCPP_ENABLE_EXPERIMENTAL")
            tc.extra_ldflags.append("-lc++experimental")
        tc.generate()

        # 上游用 dependency('libpcre')，而 pcre 配方未声明 pkg_config_name，
        # PkgConfigDeps 默认按包名只生成 pcre.pc → 从消费侧改写为 libpcre
        # （PkgConfigDeps.set_property 是 Conan 官方支持的消费侧覆盖）。
        deps = PkgConfigDeps(self)
        deps.set_property("pcre", "pkg_config_name", "libpcre")
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        if self.options.run_upstream_tests and can_run(self):
            # 跑完整上游测试套件：unit_tests（gtest 协议，11 例）+
            # 4 个 python 集成套件（database/list/search/update，27 例）。
            # 集成套件此前在 OHOS 上不可运行的唯一原因是测试夹具
            # （tests/pkgfile_test.py）给被测进程构造固定最小环境、不含 TMPDIR，
            # 而 OHOS 的 /tmp 只读 → 所有 `pkgfile -u` 用例落到只读 /tmp 报
            # "failed to create temporary file for download: Read-only file
            # system"（真机实测 rc=255）。补丁 0005 透传 TMPDIR/TMPPREFIX 后
            # 真机 38/38 全通。
            self.run(f'meson test -C "{self.build_folder}" --print-errorlogs')

    def package(self):
        meson = Meson(self)
        meson.install()
        # 上游 meson.add_install_script 会在 DESTDIR 下创建编译期默认缓存目录
        # （/var/cache/pkgfile）。包里带一个空 var/ 树没有意义，删除保持包树干净。
        package_var = os.path.join(self.package_folder, "var")
        if os.path.isdir(package_var):
            shutil.rmtree(package_var, ignore_errors=True)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        bin_path = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bin_path):
            self.runenv_info.append_path("PATH", bin_path)
            self.buildenv_info.append_path("PATH", bin_path)
