import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class WxwidgetsGtk3TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # The GUI regression also calls GLib's logging API directly.
        self.requires("glib/2.84.0.1")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure(variables={
            "WX_TEST_SHARED": bool(self.dependencies[self.tested_reference_str].options.shared)})
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info("Target execution unavailable; wx consumers not run")
            return
        # R34: 实际执行被测包链接产物（无显示 API 验证，broadway 后端
        # 不需要显示连接即可运行）
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_wxgtk3")
        self.run(f'"{bin_path}"', env="conanrun")
        if self.conf.get("user.wxwidgets:gui_tests", default=False, check_type=bool):
            gui_test = os.path.join(self.cpp.build.bindirs[0], "test_wxgtk3_gui")
            self.run(f'"{gui_test}"', env="conanrun")
        else:
            self.output.info("GUI regressions not run: set user.wxwidgets:gui_tests=True with a GTK display")
        if self.dependencies[self.tested_reference_str].options.shared:
            state_test = os.path.join(self.cpp.build.bindirs[0], "test_wx_app_state")
            self.run(f'"{state_test}"', env="conanrun")
