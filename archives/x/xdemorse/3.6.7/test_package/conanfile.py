import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class XdemorseTestConan(ConanFile):
    """消费侧验证（GUI 应用）：产物存在且可执行 + OHOS 自签证据 + 许可证。

    ⚠️ **不做运行验证**：程序需要显示服务（GTK3 窗口、瀑布图）与**声卡音频输入**
    （从电台/信号源取音），本平台两者都没有 ⇒ 结构性限制，故**不宣称**运行期可用。
    """

    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies[self.tested_reference_str].package_folder

        exe = os.path.join(pkg, "bin", "xdemorse")
        if not os.path.isfile(exe):
            raise ConanException(f"executable missing: {exe}")
        if not os.access(exe, os.X_OK):
            raise ConanException(f"executable not runnable: {exe}")
        self.output.info("可执行产物：bin/xdemorse ✓")

        if str(self.settings.os) == "OHOS":
            with open(exe, "rb") as handle:
                blob = handle.read()
            if b".codesign" not in blob and b".note.ohos" not in blob:
                raise ConanException(f"executable is not E318-signed: {exe}")
            self.output.info("可执行产物已 E318 自签 ✓")

        lic_dir = os.path.join(pkg, "licenses")
        if not os.path.isdir(lic_dir) or not os.listdir(lic_dir):
            raise ConanException(f"licenses/ missing or empty: {lic_dir}")
        self.output.info("许可证文件：%s ✓" % ", ".join(sorted(os.listdir(lic_dir))))

        if not can_run(self):
            return

        # ── 4) 真跑（rule4「能跑就必须跑」）：test_package/smoke.sh ────────────
        # L0c 要求 test_package/ 下有 .c/.cpp/.cc/.cxx/.sh/.py 之一；本脚本同时是真实验证：
        # 产物齐备 + 动态依赖可解析 + **真跑上游程序 `xdemorse -v`**。
        # 上游 `src/main.c:48` 先 `gtk_init(&argc,&argv)`、第 51 行才 `getopt("hv")`
        # ⇒ 任何选项都需要显示环境；脚本据此把「无显示」记为**有据的环境性 SKIP**（SKIP ≠ PASS），
        # 其他失败一律 FAIL（不掩盖）。
        lib_dirs = []
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lib = os.path.join(dep.package_folder, "lib")
                if os.path.isdir(lib):
                    lib_dirs.append(lib)
        smoke = os.path.join(self.recipe_folder, "smoke.sh")
        if os.path.isfile(smoke):
            self.run('sh "%s" "%s" "%s" "%s"'
                     % (smoke, pkg, os.pathsep.join(lib_dirs), self.build_folder))
            self.output.info("smoke.sh 通过 ✓（产物 + 依赖解析 + 真跑 -v 或环境性 SKIP）")

        self.output.info("应用级验证通过 ✓（GUI 需显示服务与声卡输入，不在本仓验证范围）")
