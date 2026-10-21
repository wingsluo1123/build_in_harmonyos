import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


def inject_qt6_cmakdirs(conanfile, tc):
    """qtbase 的 package_info 设了 cmake_find_mode=none，CMakeDeps 不生成 Qt6 的
    config 文件，因此显式注入 lib/cmake/<组件> 的 _DIR。"""
    try:
        pkg = conanfile.dependencies["qtbase"].package_folder
    except KeyError:
        pkg = None
    if not pkg:
        return
    cmake_dir = os.path.join(pkg, "lib", "cmake")
    if not os.path.isdir(cmake_dir):
        return
    for entry in sorted(os.listdir(cmake_dir)):
        cfg_dir = os.path.join(cmake_dir, entry)
        if os.path.isdir(cfg_dir) and os.path.isfile(
            os.path.join(cfg_dir, f"{entry}Config.cmake")
        ):
            tc.variables[f"{entry}_DIR"] = cfg_dir
    tc.variables["CMAKE_FIND_ROOT_PATH_MODE_PACKAGE"] = "BOTH"


class Qt6NoOpenGlDemoConan(ConanFile):
    """KB-NO-OPENGL 样例演示库。

    复刻真实故障形态：下游代码直接使用 QOpenGLContext/QOpenGLFunctions 且未加
    QT_NO_OPENGL 门控；在未构建 OpenGL 模块的 Qt6（OHOS qtbase）上，
    <QOpenGLContext> 转发头仍可 include 成功，但内容被 QT_NO_OPENGL 整体屏蔽，
    于是编译期报 use of undeclared identifier。

    关 SKILL：conan create 直接失败（见 reproduce.sh 阶段一）。
    开 SKILL：detect.sh 命中 → fix.sh 加门控 → conan create 通过（阶段二）。
    """

    name = "qt6-noopengl-demo"
    version = "1.0.0"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    description = (
        "Minimal demo for KB-NO-OPENGL: compiling downstream Qt6 OpenGL probe code "
        "against a Qt6 build without the OpenGL module"
    )
    license = "MIT"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "CMakeLists.txt", "src/*", "include/*"

    def requirements(self):
        self.requires("qtbase/6.11.1", transitive_headers=True, transitive_libs=True)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        inject_qt6_cmakdirs(self, tc)
        tc.generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "noopengldemo")
        self.cpp_info.set_property("cmake_target_name", "noopengldemo::noopengldemo")
        self.cpp_info.libs = ["noopengldemo"]
