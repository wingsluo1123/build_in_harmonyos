import os

from conan import ConanFile
from conan.errors import ConanException


class MystiqTestPackageConan(ConanFile):
    """test_package — mystiq 20.03.23（Qt5 GUI 转码器）

    R34: test() 通过 self.run 实质启动被测二进制，验证 Qt5 运行时依赖链闭合、
    应用在无 X11/Wayland 的 headless QPA 下能完成 GUI 初始化。
    """

    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["mystiq"]
        exe = os.path.join(pkg.package_folder, "bin", "mystiq")
        if not os.path.isfile(exe):
            raise ConanException(f"mystiq binary not found in package: {exe}")

        plugin_dirs = []
        qml_dirs = []
        for dep in self.dependencies.values():
            if not dep.package_folder:
                continue
            plugins = os.path.join(dep.package_folder, "plugins")
            if os.path.isdir(plugins):
                plugin_dirs.append(plugins)
            qml = os.path.join(dep.package_folder, "qml")
            if os.path.isdir(qml):
                qml_dirs.append(qml)

        script = os.path.join(self.recipe_folder, "test_mystiq.sh")
        self.run(
            f'sh "{script}" "{exe}" "{":".join(plugin_dirs)}" "{":".join(qml_dirs)}"',
            env="conanrun",
        )

        # 部署形态完整性：桌面/图标/metainfo 元数据随包交付
        for rel in ("share/applications/mystiq.desktop",
                    "share/icons/hicolor/scalable/apps/mystiq.svg",
                    "share/metainfo/mystiq.appdata.xml"):
            path = os.path.join(pkg.package_folder, rel)
            if not os.path.isfile(path):
                raise ConanException(f"missing packaging file: {rel}")
        self.output.info("packaging metadata present (desktop/icon/appdata)")
