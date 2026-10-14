#!/usr/bin/env python3
"""Conan test_package — laniakea 0.1.1.

实质调用被测包（R34）：
1. 布局断言：bin/ 5 个启动器、site-packages、share/laniakea、licenses 存在；
2. 以 conan python（sys.executable，laniakea-spark 同款）运行 test_laniakea.py：
   - 临时目录 pip 安装运行依赖（sqlalchemy/tomlkit/python-debian/requests/
     marshmallow/PyYAML/Pebble/click/rich/firehose/six），
     对 .so 补执行位（OHOS 加载器要求，laniakea-spark 同款）；
   - 复制系统绑定桩（test_package/stubs/：apt_pkg.py + gi/ + cryptography/
     + nacl/ + zmq/）进依赖目录——laniakea 核心 `import laniakea` 即触发
     laniakea.db → apt_pkg（Debian 专属 C 绑定，OHOS 无）；lk-archive
     全子命令注册链触发 laniakea.archive.appstream → gi/PyGObject
     （AppStream 系统绑定，OHOS 无）；laniakea.utils.traceback 顶层 import
     cryptography（AES 混淆 traceback，CLI --version 链不调用）；
     laniakea.msgstream.signing 顶层 import nacl（ed25519 签名，test_package
     signedjson 断言用 mock 键、不调用真实签名）；laniakea.msgstream.event_msg
     顶层 import zmq（ZeroMQ 消息流，签名注解求值需 Context/Socket 符号，
     5 个 CLI --version 链与 mock 键断言不创建真实 socket）。OHOS 社区源
     cryptography/PyNaCl/pyzmq wheel 的 Rust/C 扩展
     （_rust.abi3.so/_sodium.abi3.so/libzmq）在 OHOS 真机加载被拒
     （CI #91056/#91660/#91763 实测 Permission denied）。
     桩仅满足 import 期符号，真实解析/加解密/签名/socket 能力被调用即抛
     NotImplementedError（不伪造）；
   - 脚本内：import laniakea + __version__、LocalConfig（含缺 Workspace 故障路径）、
     laniakea.utils（base64/is_remote_url/listify）、deb822 Changes.add_file、
     msgstream.signedjson（mock 键）、5 个 bin 启动器 --version 实跑、数据文件断言。
3. can_run(self) 交叉保护（交叉编译时不运行消费者脚本）。
"""
import os
import stat
import sys
import tempfile

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.files import copy


class LaniakeaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["laniakea"].package_folder
        site = os.path.join(package_folder, "lib", "python3.12", "site-packages")
        share = os.path.join(package_folder, "share", "laniakea")
        bindir = os.path.join(package_folder, "bin")

        for name in ("lk-admin", "lk-archive", "lk-keytool", "rubicon", "synchrotron"):
            executable = os.path.join(bindir, name)
            if not os.path.isfile(executable):
                raise ConanException(f"missing packaged command: bin/{name}")
        if not os.path.isdir(site):
            raise ConanException("missing packaged python root: lib/python3.12/site-packages")
        if not os.path.isdir(share):
            raise ConanException("missing packaged data dir: share/laniakea")

        if not can_run(self):
            self.output.info("cross build target cannot run test_package consumer script")
            return

        with tempfile.TemporaryDirectory(prefix="laniakea-pydeps-") as temp_root:
            pydeps = os.path.join(temp_root, "pydeps")
            # 运行依赖由消费环境提供；测试期按 laniakea-spark 先例临时安装。
            # 与 laniakea-spark 重叠的包钉定其已合入 main 验证过的版本
            # （tomlkit/pyzmq/python-debian/firehose/six，OHOS 社区源有适配 wheel），
            # 其余给最低版本约束（纯 Python 包可移植；.so 包由 OHOS 社区源解析）
            self.run(
                f'"{sys.executable}" -m pip install --disable-pip-version-check '
                f"--no-cache-dir --no-compile --prefer-binary --timeout 180 "
                f'--target "{pydeps}" '
                '"tomlkit==0.15.1" "python-debian==1.1.1" '
                '"firehose==0.5" "six==1.17.0" '
                '"sqlalchemy>=2.0" "requests>=2.32" '
                '"marshmallow>=3.18" "PyYAML>=5.3" '
                '"Pebble>=4.6" "click>=7.1" "rich>=12.4"'
            )
            # OHOS 加载器校验 .so 执行位（laniakea-spark 同款）
            for root, _, files in os.walk(pydeps):
                for name in files:
                    if name.endswith(".so"):
                        path = os.path.join(root, name)
                        os.chmod(
                            path,
                            os.stat(path).st_mode
                            | stat.S_IRUSR
                            | stat.S_IRGRP
                            | stat.S_IROTH
                            | stat.S_IXUSR
                            | stat.S_IXGRP
                            | stat.S_IXOTH,
                        )

            # 系统绑定桩（apt_pkg.py + gi/ + cryptography/ + nacl/ + zmq/）
            # 复制进 pydeps：Debian/AppStream 专属 C 绑定与
            # cryptography/PyNaCl/pyzmq 的 Rust/C 扩展 OHOS 无（后者真机加载
            # Permission denied，CI #91056/#91660/#91763），桩仅满足 import 期
            # 符号，真实能力被调用即抛 NotImplementedError（不伪造）。
            # 见 stubs/ 下各文件 docstring。
            copy(
                self,
                "*",
                src=os.path.join(self.recipe_folder, "stubs"),
                dst=pydeps,
            )

            script = os.path.join(self.recipe_folder, "test_laniakea.py")
            # PYTHONPATH 由脚本内部按入参（pydeps/site）前置，无需显式 env
            self.run(
                f'"{sys.executable}" "{script}" "{package_folder}" "{site}" '
                f'"{share}" "{pydeps}" "{bindir}"'
            )
