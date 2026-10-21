"""test_package — 消费者视角验证 qt5-qttranslations 5.15.2 产物。

用 Qt5 运行时的 QTranslator 真实加载包内 translations/*.qm，证明 Qt5 应用能消费
该翻译资源包。为避免额外构建系统依赖（本仓库 CI 环境中原生 CMake 与 OHOS SDK
的 libc++ 版本可能不匹配），这里直接用工具链 clang++ 编译单个 .cpp 并运行。
"""
import os
import shlex

from conan import ConanFile
from conan.errors import ConanException


class Qt5QttranslationsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # 消费者视角：用 Qt5 运行时的 QTranslator 加载产出的 .qm。
        self.requires("qt5-qtbase/5.15.2.2")

    # ── helpers ────────────────────────────────────────────────────────

    def _find_source(self):
        name = "test_qttranslations.cpp"
        candidates = []
        for root in (self.source_folder, self.recipe_folder, self.build_folder):
            if root:
                candidates.append(os.path.join(root, name))
        base = self.build_folder
        for _ in range(4):
            candidates.append(os.path.join(base, name))
            base = os.path.dirname(base)
        for candidate in candidates:
            if os.path.isfile(candidate):
                return candidate
        raise ConanException(
            "test_qttranslations.cpp not found; searched: " + ", ".join(candidates)
        )

    def _cxx(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        return compilers.get("cpp") or compilers.get("cxx") or "clang++"

    def _cxx_runtime_lib_dirs(self):
        """从工具链 clang++ 路径推导 OHOS SDK 的 libc++/libunwind 运行库目录
        （不硬编码 SDK 版本号）。该目录含与 libQt5Core 同 ABI 的 libc++_shared.so。"""
        real = os.path.realpath(shlex.split(self._cxx())[0])
        base = os.path.dirname(real)
        candidates = (
            os.path.join(base, "..", "lib", "aarch64-linux-ohos"),
            os.path.join(base, "..", "lib"),
        )
        return [os.path.abspath(p) for p in candidates if os.path.isdir(p)]

    # ── build / test ───────────────────────────────────────────────────

    def build(self):
        qtbase = self.dependencies["qt5-qtbase"]
        include_dirs = [
            os.path.join(qtbase.package_folder, "include"),
            os.path.join(qtbase.package_folder, "include", "QtCore"),
        ]
        lib_dir = os.path.join(qtbase.package_folder, "lib")
        source = self._find_source()
        binary = os.path.join(self.build_folder, "test_qt5_qttranslations")

        cmd = " ".join(
            [shlex.quote(self._cxx()), "-std=c++17", "-fPIC", "-stdlib=libc++"]
            + [f"-I{shlex.quote(d)}" for d in include_dirs]
            + [shlex.quote(source)]
            + [f"-L{shlex.quote(lib_dir)}", "-lQt5Core"]
            + [f"-o {shlex.quote(binary)}"]
        )
        self.run(cmd)
        if not os.path.isfile(binary):
            raise ConanException(f"failed to build test binary: {binary}")

    def test(self):
        translations = self.dependencies["qt5-qttranslations"]
        qtbase = self.dependencies["qt5-qtbase"]

        # 被测包通过 runenv_info 声明的翻译目录（等价 Qt5 QT_INSTALL_TRANSLATIONS）
        tr_dir = os.path.join(translations.package_folder, "translations")

        # 测试二进制动态链接 libQt5Core + libc++_shared：显式构造 LD_LIBRARY_PATH
        # （qtbase 包 lib/ + OHOS SDK 的 libc++ 目录），并在命令行内联赋值，
        # 避免被外层 conan build/run 环境的 LD_LIBRARY_PATH 覆盖。
        lib_dirs = [os.path.join(qtbase.package_folder, "lib")]
        lib_dirs += self._cxx_runtime_lib_dirs()
        env_prefix = " ".join(
            [
                f"QT_TRANSLATIONS_PATH={shlex.quote(tr_dir)}",
                f"LD_LIBRARY_PATH={shlex.quote(':'.join(lib_dirs))}",
            ]
        )
        binary = os.path.join(self.build_folder, "test_qt5_qttranslations")
        self.run(f"{env_prefix} {shlex.quote(binary)}", ignore_errors=False)
