#!/usr/bin/env python3
"""Conan recipe for kcachegrind 26.04.0 on HarmonyOS PC.

KCachegrind 是 KDE 的性能剖析数据可视化工具（callgrind/cachegrind/valgrind
输出浏览器），KDE Gear 26.04.0（invent.kde.org/sdk/kcachegrind），Qt6/KF6
纯 Qt Widgets GUI 应用 + 命令行转换脚本。构建产物：
`bin/kcachegrind`、`bin/{dprof2calltree,hotshot2calltree,memprof2calltree,
op2calltree,pprof2calltree}`（转换脚本）。

上游 `CMakeLists.txt` 实测直接依赖：
```
find_package(Qt6 6.5.0 REQUIRED Core DBus Gui Widgets)
find_package(KF6 6.0.0 REQUIRED
    Archive CoreAddons WidgetsAddons XmlGui I18n Config KIO DBusAddons)
find_package(KF6DocTools 6.0.0)   # TYPE OPTIONAL
find_package(ECM 6.0.0 REQUIRED NO_MODULE)
```
`kcachegrind/CMakeLists.txt` 的 target_link_libraries 另含
`KF6::ConfigCore/KF6::ConfigGui`（kconfig 提供前者、kconfigwidgets 提供后者）
与 `KF6::KIOCore/KF6::KIOWidgets`。

OHOS 适配要点（与 ktimer/kteatime 26.04.0 同族口径）：
  - **Qt6 DBus 由 qtbase/6.11.1.1（FEATURE_dbus=ON）提供**：上游 main.cpp
    构造 `KDBusService`（kdbusaddons）需要 Qt6DBus，故选 dbus=ON 变体；
    其 `override=True` 统一掉 kio 等包内部钉的 qtbase/6.11.1。
  - **KF6 闭包取 6.18 线 + kio/6.14.0**：上游需要 `KF6::KIOWidgets`
    （kcachegrind/CMakeLists.txt 显式链接），而 ohpcd 上的 kio/6.26.0 是
    `KIOCORE_ONLY` 变体（不含 KIOWidgets/KIOGui/KIOFileWidgets），
    kio/6.14.0 才是带 KIOWidgets 的完整变体 ⇒ 取 kio/6.14.0，并用
    `override=True` 把它内部的 6.14 钉版抬到 6.18 线（ktimer 26.04.0 同款，
    唯一代价是 kio 本地重建；其配方自带 BUILD_TESTING=OFF，不跑上游测试）。
    源码侧实证：kcachegrind 只用到 `KIO::file_copy`（KIOCore）与
    `KJobWidgets::setWindow`（kjobwidgets），KIOWidgets 仅为链接期目标。
  - **karchive/6.19.0**：kiconthemes/6.18.0 的**已发布二进制**钉的就是它，
    对齐可命中二进制；karchive 安装的 KF6ArchiveConfig.cmake 会
    `find_dependency(OpenSSL)` ⇒ openssl 必须进图并下载二进制（ktimer 先例）。
  - KF_IGNORE_PLATFORM_CHECK=TRUE（OHOS 不在 KDE 平台列表）
  - KF_SKIP_PO_PROCESSING=ON（ki18n_install(po) 的 msgfmt/lconvert 在本平台
    不可用，.qm 翻译目录非必需）
  - **KF6DocTools 不在发布闭包内**：上游 `find_package(KF6DocTools)` 非 REQUIRED，
    `doc/` 与 `kdoctools_install(po)` 由 `KF6DocTools_FOUND` 守卫 ⇒ 无需补丁，
    代价仅是在线手册不可用。
  - ECM_MODULE_PATH 手工设置 + conan_cmakedeps_paths.cmake
    （qtbase 与 KF6 包用 cmake_find_mode=none，CMakeDeps 不会把 lib/cmake
    加进 CMAKE_PREFIX_PATH）
  - 主二进制 RPATH 注入（kteatime/ktimer 26.04.0 先例）：OHOS musl 加载器不认
    LD_LIBRARY_PATH，而 Qt6/KF6 预编译包普遍没有 DT_RPATH/DT_RUNPATH ⇒
    用 `-Wl,--disable-new-dtags -Wl,-rpath,<dep libs>` 写 **DT_RPATH**
    （对整棵依赖树生效，可解析裸名 NEEDED）。
  - `-Wl,-z,max-page-size=0x1000` 钉 4K 页布局（audiocd/ktuberling 先例）。
  - 上游 kcachegrind 26.04.0 无任何测试目标（无 tests/、无 add_test/
    enable_testing/BUILD_TESTING），MANIFEST 如实申报 0；消费者验证由
    test_package 冒烟承担（offscreen 运行安装后的 bin/kcachegrind）。
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)


class KcachegrindConan(ConanFile):
    name = "kcachegrind"
    version = "26.04.0"
    description = (
        "KDE profile data visualizer (Callgrind/Cachegrind frontend) "
        "for HarmonyOS PC"
    )
    license = "GPL-2.0-or-later"
    homepage = "https://invent.kde.org/sdk/kcachegrind"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Qt6 Core/Gui/Widgets/DBus 唯一提供者（6.11.1.1 = FEATURE_dbus=ON，
        # 上游 main.cpp 的 KDBusService 需要 Qt6DBus）；override 统一 kio 等
        # 内部钉的 qtbase/6.11.1。
        self.requires("qtbase/6.11.1.1", override=True)
        # 上游 main.cpp: KDBusService service(KDBusService::Multiple);
        self.requires("kdbusaddons/6.29.0")
        # 上游 find_package(KF6 ... KIO)：必须是带 KIOWidgets 的完整变体。
        self.requires("kio/6.14.0")
        # 上游 find_package(KF6 ... XmlGui) + target_link_libraries KF6::XmlGui
        self.requires("kxmlgui/6.18.0")
        # 上游 link KF6::ConfigGui（kconfigwidgets）/ KF6::ConfigCore（kconfig）
        self.requires("kconfigwidgets/6.18.0")
        # 把 kio/6.14.0 内部钉的 6.14 线统一抬到 6.18 线（ktimer 先例）。
        for dep in (
            "kconfig",
            "kcoreaddons",
            "ki18n",
            "kservice",
            "kcolorscheme",
            "kcompletion",
            "kguiaddons",
            "kiconthemes",
            "kitemviews",
            "kjobwidgets",
            "kwidgetsaddons",
            "kwindowsystem",
            "kauth",
            "solid",
            "kbookmarks",
            "kcodecs",
            "kcrash",
            "knotifications",
        ):
            self.requires(f"{dep}/6.18.0", override=True)
        # ★kiconthemes/6.18.0 的已发布二进制钉 karchive/6.19.0；对齐它可命中
        # 二进制（免掉 kiconthemes 本地重建及其会挂的上游测试）。karchive 上传的
        # KF6ArchiveConfig.cmake 硬性 find_dependency(OpenSSL)。
        self.requires("karchive/6.19.0", override=True)
        # 让 openssl 的**二进制必下载**（ktimer 26.04.0 先例）：karchive 配方
        # 自己不声明 openssl，只经 kiconthemes 传递进来时 conan 视其
        # headers=False/libs=False 而 BINARY_SKIP，导致下游 configure 找不到
        # OpenSSL（CI worker 无系统 OpenSSL）。
        self.requires("openssl/3.5.6.1")
        # OHOS SDK lld 链接期需要 libxml2.so.16（libxml2/2.15.3 的 SONAME）；
        # 见 _cmake_build_env()（kio/kservice 同款机制）。
        self.requires("libxml2/2.15.3")

    def build_requirements(self):
        # 上游 find_package(ECM ${KF_MIN_VERSION} REQUIRED NO_MODULE)。
        # kdbusaddons/6.29.0 的 tool_requires 也带 ECM 6.29.0，口径一致。
        self.tool_requires("extra-cmake-modules/6.29.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        # ki18n_install(po) 的 msgfmt/lconvert 在本平台不可用，.qm 非必需。
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"

        # OHOS musl loader 页布局 workaround（audiocd/ktuberling/ktimer 先例）。
        link_flags = []
        if self.settings.os == "OHOS":
            link_flags.append("-Wl,-z,max-page-size=0x1000")
            tc.variables["CMAKE_SHARED_LINKER_FLAGS_INIT"] = (
                "-Wl,-z,max-page-size=0x1000"
            )

        # ECM 自己安装的 ECMConfig.cmake 会设 ECM_MODULE_PATH，CMakeDeps 生成的
        # 那份不传播 ⇒ 手工设置（kxmlgui/kteatime/ktimer 同款）。
        ecm = self.dependencies.build.get("extra-cmake-modules")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join(
                os.path.join(ecm_share, rel)
                for rel in ("modules", "find-modules", "kde-modules")
            )

        self._write_cmake_paths(ecm)

        # 主二进制 RPATH 注入：OHOS musl 加载器不认 LD_LIBRARY_PATH，而
        # Qt6/KF6 预编译包没有 DT_RPATH/DT_RUNPATH ⇒ 必须写进 ELF。
        # ① CMAKE_BUILD_RPATH 是 CMake 列表语义、必须用 ';'；
        # ② 兜底用 -Wl,--disable-new-dtags 产出 **DT_RPATH**（对整棵依赖树生效，
        #    覆盖自身无 RUNPATH 的 KF6 包去解析裸名 NEEDED）。
        dep_lib_dirs = [
            os.path.join(d.package_folder, "lib")
            for d in self.dependencies.values()
            if d and d.package_folder
            and os.path.isdir(os.path.join(d.package_folder, "lib"))
        ]
        if dep_lib_dirs:
            tc.variables["CMAKE_BUILD_RPATH"] = ";".join(dep_lib_dirs)
            tc.variables["CMAKE_INSTALL_RPATH"] = ";".join(dep_lib_dirs)
            link_flags += [
                "-Wl,--disable-new-dtags",
                "-Wl,-rpath," + os.pathsep.join(dep_lib_dirs),
            ]

        if link_flags:
            tc.variables["CMAKE_EXE_LINKER_FLAGS_INIT"] = " ".join(link_flags)

        tc.generate()

    def _write_cmake_paths(self, ecm):
        # qtbase/KF6 包 cmake_find_mode=none ⇒ CMakeDeps 不会把它们的
        # lib/cmake 放进 CMAKE_PREFIX_PATH，手工写 conan_cmakedeps_paths.cmake
        # （kxmlgui/libkdegames/ktimer 26.04.0 同款）。
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        for dep in list(self.dependencies.values()) + list(
            self.dependencies.build.values()
        ):
            if dep and dep.package_folder:
                self._append_dependency_paths(lines, dep.package_folder)
        if ecm and ecm.package_folder:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            lines.extend(
                [
                    f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_share}/cmake")',
                    f'list(PREPEND CMAKE_MODULE_PATH "{ecm_share}/modules")',
                    f'list(PREPEND CMAKE_MODULE_PATH "{ecm_share}/find-modules")',
                    f'list(PREPEND CMAKE_MODULE_PATH "{ecm_share}/kde-modules")',
                ]
            )
        lines.extend(
            [
                'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")',
                'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")',
            ]
        )
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    @staticmethod
    def _append_dependency_paths(lines, package_folder):
        lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{package_folder}/lib/cmake")')
        lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{package_folder}")')
        lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{package_folder}/lib")')
        lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{package_folder}/include")')

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        dep_lib_dirs = [
            os.path.join(d.package_folder, "lib")
            for d in self.dependencies.values()
            if d and d.package_folder
            and os.path.isdir(os.path.join(d.package_folder, "lib"))
        ]
        rpath = ";".join(dep_lib_dirs) if dep_lib_dirs else None
        with self._cmake_build_env().vars(self).apply():
            cmake.configure(
                variables={"CMAKE_BUILD_RPATH": rpath,
                           "CMAKE_INSTALL_RPATH": rpath} if rpath else None)
            cmake.build()

    def _cmake_build_env(self):
        # 构建期 host 工具（moc/uic/rcc/kconfig_compiler/lconvert）是 conan 包里的
        # OHOS 二进制 ⇒ 需要依赖 lib 目录 + /system/lib64 的 libc++_shared。
        build_env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                build_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
        if self.settings.os == "OHOS":
            # OHOS SDK lld 依赖 SDK llvm/lib 里的 libxml2，CI worker 不一定导出。
            for llvm_lib in sorted(
                glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"
                )
            ):
                build_env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
            # 沙箱 LD_LIBRARY_PATH 里有不兼容的 libc++_shared，先压 /system/lib64。
            build_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return build_env

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # 应用包：bin/kcachegrind + 转换脚本，无库交付物。
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_find_mode", "none")
        # 运行期加载 Qt6/KF6 依赖：把依赖 lib 目录写进 runenv，
        # 消费者 test_package 的 conanrun 可直接解析。
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib")
        )
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                self.runenv_info.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
                self.runenv_info.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins")
                )
                self.runenv_info.prepend_path(
                    "QT_PLUGIN_PATH",
                    os.path.join(dep.package_folder, "lib", "plugins"),
                )

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanException(
                "kcachegrind/26.04.0 is a HarmonyOS PC adaptation "
                "(R32: os 判断用 in)"
            )
