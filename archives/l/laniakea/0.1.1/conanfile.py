#!/usr/bin/env python3
"""Conan recipe — laniakea 0.1.1（纯 Python Debian 衍生发行版管理套件）。

上游 lkhq/laniakea 官方 tag v0.1.1，Meson 构建；但 meson.build 强依赖
systemd/apt-ftparchive/bubblewrap/GLibc renameat2 等 Debian 专属工具，
OHOS 无，因此不跑 Meson/pip，改为纯 Python 手动复制打包
（参考同生态 laniakea-spark/0.1.1 与 pyjson5/0.15.0 先例）：

- 全部顶层 Python 包复制到 lib/python3.12/site-packages/（PYTHONPATH 导入路径）
- bin/ 生成 5 个 CLI 启动器包装（lk-admin/lk-archive/lk-keytool/rubicon/synchrotron，
  对应上游 meson install_data(... rename: 'lk-*') 装到 bin/ 的入口）
- data/ → share/laniakea/；同时镜像一份到 lib/python3.12/data/
  （匹配上游 get_data_file() 非 /usr 安装的"开发目录"启发式
  ``<module>/../../data/``，使 LintianConfig() 等数据文件在 conan 布局可发现）
- package() 生成最小默认 base-config.toml（上游 data/ 无此文件，仅在
  contrib/base-config.toml.sample；管理员运行时在 /etc/laniakea/ 创建），
  写入 share/laniakea/ 与 lib/python3.12/data/，使无参 LocalConfig() 可发现
- COPYING → licenses/
- requires python/3.12.9（ohpcd 制品仓已发布，W0 已确认）；其余 Python 运行依赖
  （sqlalchemy/cryptography/pyzmq/python-debian/tomlkit/click/rich 等）由消费环境
  提供，不声明 native target 依赖（与 laniakea-spark 一致）
- R38：产物含可执行 CLI → 软件级 commands.json 声明
- R26 不适用（纯 Python 无 .so）；R32 validate() 按 ("Linux", "OHOS") 判断；
  R33 无编译环境变量依赖（build() 仅 compileall 语法检查，解释器取 sys.executable）
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    save,
)
from conan.tools.layout import basic_layout


class LaniakeaConan(ConanFile):
    name = "laniakea"
    version = "0.1.1"
    description = "Suite of tools to manage a Debian-based Linux distribution"
    license = "LGPL-3.0-or-later"
    homepage = "https://laniakea-hq.readthedocs.io/"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    # src/ 下的顶层 Python 包目录（keytool/ 为目录非包：仅 keytool.py 单文件
    # + meson.build，无 __init__.py，其 keytool.py 在 package() 中单独复制）
    _module_dirs = [
        "admincli",
        "archivecli",
        "debcheck",
        "laniakea",
        "lighthouse",
        "lkscheduler",
        "mailgun",
        "mirk",
        "planter",
        "rubicon",
        "spears",
        "synchrotron",
        "webdash",
        "webswview",
        "webupload",
    ]

    # bin/ 启动器：{命令名: 包装体（site-packages 已前置进 sys.path）}
    _launchers = {
        "lk-admin": (
            "from admincli import cli\n"
            "sys.exit(cli.run(os.path.abspath(__file__), sys.argv[1:]))"
        ),
        "lk-archive": (
            "from archivecli import cli\n"
            "sys.exit(cli.run(os.path.abspath(__file__), sys.argv[1:]))"
        ),
        "lk-keytool": (
            "from keytool import run\n"
            "sys.exit(run(sys.argv[1:]))"
        ),
        "rubicon": (
            "from rubicon import cli\n"
            "sys.exit(cli.run(os.path.abspath(__file__), sys.argv[1:]))"
        ),
        "synchrotron": (
            "from synchrotron import cli\n"
            "sys.exit(cli.run(os.path.abspath(__file__), sys.argv[1:]))"
        ),
    }

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32：OHOS 作为 Linux-like 平台命中
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"Unsupported operating system: {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires("python/3.12.9")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # 无编译：对打包的全部模块做字节码语法检查（compileall 只编译不 import，
        # 不需要 apt_pkg 等 Debian 专属绑定）。解释器来自 Python 运行时，
        # 不依赖任何 shell 环境变量（R33）。
        src_dir = os.path.join(self.source_folder, "src")
        self.run(f'"{sys.executable}" -m compileall -q "{src_dir}"')

    def _package_module(self, name, site_dir):
        """把 src/<name> 目录复制到 site-packages（排除构建/缓存文件）。"""
        src = os.path.join(self.source_folder, "src", name)
        if not os.path.isdir(src):
            return
        copy(
            self,
            "*",
            src=src,
            dst=os.path.join(site_dir, name),
            excludes=("meson.build", "*.pyc", "*/__pycache__/*"),
        )

    def package(self):
        python_root = os.path.join(self.package_folder, "lib", "python3.12")
        site_dir = os.path.join(python_root, "site-packages")

        # 1) 全部顶层 Python 包 → site-packages
        for mod in self._module_dirs:
            self._package_module(mod, site_dir)
        # keytool：src/keytool/ 目录（含单文件模块 keytool.py + meson.build，
        # 无 __init__.py 不是包）；上游把 keytool.py 安装为 bin/lk-keytool。
        # 此处把 src/keytool/keytool.py 复制为 site-packages/keytool.py 模块，
        # 使 bin/lk-keytool 包装器 `from keytool import run` 按模块导入成立。
        copy(
            self,
            "keytool.py",
            src=os.path.join(self.source_folder, "src", "keytool"),
            dst=site_dir,
            keep_path=False,
        )

        # 2) 数据 → share/laniakea/（标准位置）+ lib/python3.12/data/
        #    （get_data_file 开发目录启发式镜像，见模块 docstring）
        data_src = os.path.join(self.source_folder, "data")
        copy(
            self,
            "*",
            src=data_src,
            dst=os.path.join(self.package_folder, "share", "laniakea"),
            excludes=("meson.build",),
        )
        copy(
            self,
            "*",
            src=data_src,
            dst=os.path.join(python_root, "data"),
            excludes=("meson.build",),
        )

        # 2.5) 生成最小默认 base-config.toml：上游 data/ 不含此文件（仅在
        #      contrib/base-config.toml.sample，管理员运行时创建于 /etc/laniakea/）。
        #      无参 LocalConfig() 经 get_config_file → get_data_file 查找：
        #      /etc/laniakea/base-config.toml（沙箱无）→ dev 启发式
        #      <pkg>/lib/python3.12/data/base-config.toml（此处命中）。
        #      写入标准数据位 share/laniakea/（/usr 前缀兜底分支）保持一致。
        #      仅占位默认值，无真实凭据；管理员可 /etc/laniakea/ 覆盖。
        base_config = (
            "# Laniakea 基础配置（OHOS 适配 package() 生成的最小默认占位配置，无真实凭据）\n"
            "# 管理员可在 /etc/laniakea/base-config.toml 覆盖\n"
            'Workspace = "/var/tmp/laniakea"\n'
            "\n"
            "[Database]\n"
            'db = "laniakea"\n'
            'user = "laniakea-user"\n'
            'password = ""\n'
            'host = "localhost"\n'
            "port = 5432\n"
            "\n"
            "[Archive]\n"
            'master_repo_name = "master"\n'
        )
        for dst_dir in (
            os.path.join(self.package_folder, "share", "laniakea"),
            os.path.join(python_root, "data"),
        ):
            save(self, os.path.join(dst_dir, "base-config.toml"), base_config)

        # 3) LICENSE
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

        # 4) bin/ 启动器包装（R38：CLI 包必须可执行）
        wrapper_head = (
            "#!/usr/bin/env python3\n"
            "import os\n"
            "import sys\n"
            "\n"
            "_pkg_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))\n"
            "_site = os.path.join(_pkg_dir, 'lib', 'python3.12', 'site-packages')\n"
            "if _site not in sys.path:\n"
            "    sys.path.insert(0, _site)\n"
            "\n"
            "# pwd 兼容兜底：沙箱/容器运行 uid 无 /etc/passwd 条目（如 CI worker\n"
            "# uid=20020101）时，仅为当前 uid 提供占位条目（其它 uid 实参转发真实\n"
            "# 函数，不污染 root 等查询），使 ensure_laniakea_master_user 的\n"
            "# pwd.getpwuid(os.getuid()) 不崩溃；warn_only=True 调用者（lk-admin/\n"
            "# lk-archive/synchrotron）走警告分支，rubicon 非 --version 路径在无\n"
            "# passwd 环境将 exit(6)（上游默认）；有 passwd 条目的环境不命中 try 分支、零影响\n"
            "import pwd as _pwd\n"
            "try:\n"
            "    _pwd.getpwuid(os.getuid())\n"
            "except KeyError:\n"
            "    import collections as _c\n"
            "    _Pw = _c.namedtuple('pw', ['pw_name', 'pw_passwd', 'pw_uid',\n"
            "                               'pw_gid', 'pw_gecos', 'pw_dir', 'pw_shell'])\n"
            "    _uid = os.getuid()\n"
            "    _real_getpwuid = _pwd.getpwuid\n"
            "    def _getpwuid(_u):\n"
            "        if _u == _uid:\n"
            "            return _Pw('user%d' % _u, 'x', _u, _u, '', '/tmp', '/bin/sh')\n"
            "        return _real_getpwuid(_u)\n"
            "    _pwd.getpwuid = _getpwuid\n"
            "\n"
        )
        for cmd, body in self._launchers.items():
            wrapper = wrapper_head + body + "\n"
            path = os.path.join(self.package_folder, "bin", cmd)
            save(self, path, wrapper)
            os.chmod(path, 0o755)  # save() 默认无执行位；CLI 必须可执行

    def package_id(self):
        # 无编译产物 → 单一 package_id（与 pyjson5/laniakea-spark 一致）
        self.info.clear()

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []

        site = os.path.join(self.package_folder, "lib", "python3.12", "site-packages")
        # 运行期环境：PYTHONPATH 指向 site-packages，PATH 含 bin
        self.runenv_info.prepend_path("PYTHONPATH", site)
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
        self.buildenv_info.prepend_path("PYTHONPATH", site)
