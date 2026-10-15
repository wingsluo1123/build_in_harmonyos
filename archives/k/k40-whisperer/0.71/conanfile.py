#!/usr/bin/env python3
"""Conan recipe — k40-whisperer 0.71（纯 Python K40 激光雕刻机控制软件，tkinter GUI）。

上游为 tkinter GUI 应用（k40_whisperer.py 主程序），纯 Python（21 个 .py、
0 个 C/C++ 源文件），无编译。Python 类适配（R47 python_class_task，
无构建/打包族，仿 archives/p/pyjson5/0.15.0 先例）。

适配要点：
- 无编译：build() 不定义（不伪造编译日志，R34 由 test_package 实质执行保证）
- 解释器：requires python/3.12.9（ohpcd 已发布二进制，CI 可复现）
- 硬依赖：requires pillow/10.4.0（svg_reader.py L35、k40_whisperer.py L86-88
  模块级 from PIL import ... 无 try 保护；pillow/10.4.0 已发布 status=published）
- lxml：svg_reader.py L38 / inkex.py L35 硬 import（无 try 保护），但 ohpcd 制品仓
  仅有 built 未发布配方 → 按 R36 不声明，作为已知依赖缺口在 notes.md/test_package
  如实标注；lxml 发布前 svg_reader/inkex 不可导入，SVG 解析功能不可用
- pyclipper/pyusb：上游代码自身 try/except 可选降级（k40_whisperer.py L105-110、
  nano_library.py L21-26 仅打印提示），与上游行为一致不声明
- tkinter：OHOS python/3.12.9 缺 _tkinter → GUI 主程序 import 阶段即失败，
  不可运行（R40 深度适配如实标注，不编造 GUI 可用）；核心算法模块
  （egv/dxf/interpolate/ecoords/convex_hull/g_code_library/LaserSpeed）
  纯 stdlib 可独立导入，test_package 实质调用
- 布局：lib/python3.12/site-packages/（全部模块，import 直接可用）
  + bin/k40-whisperer（启动包装：--version/--help 直接响应，真实启动在
  OHOS 因缺 _tkinter/lxml 失败时给出明确诊断 exit 1，不静默崩溃）
- R38：产物含可执行入口 bin/k40-whisperer → 软件级 commands.json 声明
- R26 不适用（无系统同名库冲突）；R32 不适用（无 C 编译 settings.os 分支）；
  R33 不适用（build() 无 self.run，test_package 仅注入 env 变量）
"""
import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    save,
)
from conan.tools.layout import basic_layout


class K40WhispererConan(ConanFile):
    name = "k40-whisperer"
    version = "0.71"
    description = "K40 Whisperer - laser cutter control software for the K40 (tkinter GUI, SVG/DXF to EGV)"
    license = "GPL-3.0"
    homepage = "https://www.scorchworks.com/K40whisperer/k40_whisperer.html"
    url = "https://www.scorchworks.com/K40whisperer/k40_whisperer.html"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("python/3.12.9")
        self.requires("pillow/10.4.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # 无编译（纯 Python 只装不编，R34 由 test_package 实质执行保证）
        apply_conandata_patches(self)

    def package(self):
        # 纯 Python 模块 → site-packages（PYTHONPATH 导入路径）
        site = os.path.join(self.package_folder, "lib", "python3.12", "site-packages")
        copy(self, "*.py",
             src=self.source_folder,
             dst=site)
        # 许可证
        copy(self, "gpl-3.0.txt",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)
        # console 等价包装：bin/k40-whisperer（--version/--help 直接响应；
        # 真实启动导入 k40_whisperer 等同 python k40_whisperer.py，OHOS 缺
        # _tkinter/lxml 时给出明确诊断而非静默崩溃）
        wrapper = (
            "#!/usr/bin/env python3\n"
            "\"\"\"k40-whisperer - K40 激光雕刻机控制软件启动器（k40_whisperer.py 的 console 等价包装）。\"\"\"\n"
            "import os\n"
            "import sys\n"
            "\n"
            "_pkg_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))\n"
            "_site = os.path.join(_pkg_dir, 'lib', 'python3.12', 'site-packages')\n"
            "if _site not in sys.path:\n"
            "    sys.path.insert(0, _site)\n"
            "\n"
            "def _show_version():\n"
            "    sys.stdout.write('K40 Whisperer 0.71\\n')\n"
            "\n"
            "def _show_help():\n"
            "    sys.stdout.write('Usage: k40-whisperer [-h|--help] [--version]\\n')\n"
            "    sys.stdout.write('K40 激光雕刻机控制软件（tkinter GUI，读取 SVG/DXF 生成 EGV 指令）。\\n')\n"
            "    sys.stdout.write('  -h, --help    print this help\\n')\n"
            "    sys.stdout.write('  --version     print version\\n')\n"
            "\n"
            "if __name__ == '__main__':\n"
            "    argv = sys.argv[1:]\n"
            "    if '--version' in argv:\n"
            "        _show_version()\n"
            "        sys.exit(0)\n"
            "    if '-h' in argv or '--help' in argv:\n"
            "        _show_help()\n"
            "        sys.exit(0)\n"
            "    # 真实启动：导入 k40_whisperer（模块级即构建 Tk 界面并 mainloop，\n"
            "    # 等同 python k40_whisperer.py）。OHOS python3.12 缺 _tkinter 且\n"
            "    # lxml 未随制品仓发布时，导入即失败 → 给出明确诊断而非静默崩溃。\n"
            "    try:\n"
            "        import k40_whisperer  # noqa: E402,F401\n"
            "    except ImportError as exc:\n"
            "        sys.stderr.write('k40-whisperer: GUI 无法启动: %s\\n' % exc)\n"
            "        sys.stderr.write('k40-whisperer: OHOS python3.12 缺少 _tkinter（且 svg_reader 依赖的 '\n"
            "                         'lxml 尚未发布到制品仓），tkinter GUI 在鸿蒙上暂不可用；\\n')\n"
            "        sys.stderr.write('k40-whisperer: 核心算法模块（egv/dxf/interpolate/ecoords/'\n"
            "                         'convex_hull/g_code_library）可直接 import 使用。\\n')\n"
            "        sys.exit(1)\n"
        )
        save(self, os.path.join(self.package_folder, "bin", "k40-whisperer"), wrapper)
        # save() 默认无执行位；CLI 必须可执行（R38/L0k，直接运行）
        os.chmod(os.path.join(self.package_folder, "bin", "k40-whisperer"), 0o755)

    def package_id(self):
        self.info.clear()  # 无编译产物 → 单一 package_id

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        # 运行期环境：PYTHONPATH 指向 site-packages，PATH 含 bin
        site = os.path.join(self.package_folder, "lib", "python3.12", "site-packages")
        self.runenv_info.prepend_path("PYTHONPATH", site)
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
