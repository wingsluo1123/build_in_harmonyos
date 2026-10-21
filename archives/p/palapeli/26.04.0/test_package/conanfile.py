import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import save


class PalapeliTestPackage(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # qtbase/qtsvg 以及 KF6 各包在制品仓里都是 cmake_find_mode=none，
        # CMakeDeps 不会把它们的 lib/cmake 加进 CMAKE_PREFIX_PATH；不补这段，
        # find_package(Pala) 里 PalaConfig 的 find_dependency(Qt6 ...) 必然无解。
        # 与 palapeli 自身构建期的手写路径逻辑保持一致：
        #   全量 prepend，最后再 prepend 一次 qtbase-sql-dbus，使其排在最前，
        #   保证带 DBus 的 Qt6 变体优先命中。
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        for dep in self.dependencies.values():
            if dep.package_folder:
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{dep.package_folder}/lib/cmake")')
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{dep.package_folder}")')
        for dep in self.dependencies.values():
            if dep.ref.name == "qtbase-sql-dbus" and dep.package_folder:
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{dep.package_folder}/lib/cmake")')
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{dep.package_folder}")')
        # conan_toolchain.cmake 会 include 同名文件（Conan 2 约定）
        save(self, os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake"),
             "\n".join(lines) + "\n")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info("cross-compiling: execution skipped")
            return

        pkg = self.dependencies["palapeli"].package_folder
        plugin_dir = os.path.join(pkg, "lib", "plugins", "palapelislicers")

        # 1) 真实消费者：链接导出的 Pala 包，加载已安装的切片器插件并跑通切图算法
        env = Environment()
        env.define("PALAPELI_PLUGIN_DIR", plugin_dir)
        with env.vars(self).apply():
            self.run(os.path.join(self.cpp.build.bindirs[0], "palapeli_consumer"),
                     env="conanrun")

        # 2) 安装产物与 ELF 可移植性断言（E537 口径：不得留下路径型 DT_NEEDED）
        self.run(f'sh "{os.path.join(self.recipe_folder, "test_palapeli.sh")}" "{pkg}"',
                 env="conanrun")
