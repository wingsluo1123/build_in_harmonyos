#!/usr/bin/env python3
"""test_package — picotts 已安装产物的消费者测试。

两条独立验证链：
  1. picotts_engine_contract（CMake 消费方，链接 picotts::picotts）
     —— 真实调用 pico_* 公共 API，端到端合成一段语音并断言 PCM 输出非空、
        采样格式为 PICO_DATA_PCM_16BIT。语音资源目录由包内
        share/pico/lang 的绝对路径显式传入。
  2. cli_test.sh
     —— 对已安装的 bin/pico2wave 做真实行为测试（含 readelf NEEDED 链路校验）。

OHOS 备注：新编译出的消费者 ELF 必须先自签名才能执行（真机 SELinux/MAC
策略），运行时目录用可写的 /data/storage/el2/base/cache（与 libXext 1.3.7
同一成熟模式）。
"""
import os
import shutil
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


TEST_EXECUTABLES = ("picotts_engine_contract", "picotts_wav_consumer")


class PicottsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "CMakeLists.txt", "*.c", "cli_test.sh"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            raise ConanException("picotts consumers are not runnable")

        package_folder = self.dependencies["picotts"].package_folder
        lingware_dir = os.path.join(package_folder, "share", "pico", "lang")
        if not os.path.isdir(lingware_dir):
            raise ConanException(
                "packaged lingware directory is missing: {}".format(lingware_dir)
            )
        binary = os.path.join(package_folder, "bin", "pico2wave")
        if not os.path.isfile(binary):
            raise ConanException(
                "packaged pico2wave binary is missing: {}".format(binary)
            )

        runtime_dir = None
        if str(self.settings.os) == "OHOS":
            runtime_dir = tempfile.mkdtemp(
                prefix="picotts-test-", dir="/data/storage/el2/base/cache"
            )
        try:
            executables = {}
            for name in TEST_EXECUTABLES:
                built = os.path.join(self.cpp.build.bindir, name)
                if runtime_dir is not None:
                    staged = os.path.join(runtime_dir, name)
                    shutil.copy2(built, staged)
                    self._sign_ohos_elf(staged)
                    built = staged
                executables[name] = built

            # 1. 库 API 端到端合成（真实加载包内语音资源）
            self.run(
                '"{}" "{}"'.format(
                    executables["picotts_engine_contract"], lingware_dir
                ),
                env="conanrun",
            )

            # 2. 鸿蒙 PC 消费者端到端用例：合成 -> 落盘 WAV -> 解析校验容器。
            #    OHOS 根为只读，输出落在 /data/storage/el2/base/cache 的沙箱目录。
            wav_out = os.path.join(
                runtime_dir or self.build_folder, "picotts-consumer.wav"
            )
            if os.path.isfile(wav_out):
                os.remove(wav_out)
            self.run(
                '"{}" "{}" "{}"'.format(
                    executables["picotts_wav_consumer"], lingware_dir, wav_out
                ),
                env="conanrun",
            )
            if not os.path.isfile(wav_out) or os.path.getsize(wav_out) <= 44:
                raise ConanException(
                    "consumer WAV was not produced: {}".format(wav_out)
                )
            self.output.info(
                "picotts: consumer WAV produced ({} bytes): {}".format(
                    os.path.getsize(wav_out), wav_out
                )
            )

            # 2. 已安装 CLI 的真实行为 + 链接链路校验
            #    cmake_layout 下 test() 的 cwd 是构建目录，故脚本取绝对路径。
            cli_script = os.path.join(self.recipe_folder, "cli_test.sh")
            if not os.path.isfile(cli_script):
                raise ConanException(
                    "cli_test.sh is missing from the test package: {}".format(cli_script)
                )
            bash = os.environ.get("CONFIG_SHELL", "bash")
            self.run(
                '"{}" "{}" "{}"'.format(bash, cli_script, package_folder),
                env="conanrun",
            )
        finally:
            if runtime_dir is not None:
                shutil.rmtree(runtime_dir)

    def _sign_ohos_elf(self, path):
        signer = shutil.which("binary-sign-tool") or (
            "/data/service/hnp/bin/binary-sign-tool"
        )
        readelf = shutil.which("llvm-readelf") or (
            "/data/service/hnp/bin/llvm-readelf"
        )
        if not os.path.isfile(signer) or not os.path.isfile(readelf):
            raise ConanException("required OHOS signing tools are missing")
        temporary = "{}.signed".format(path)
        subprocess.run(
            [
                signer,
                "sign",
                "-inFile",
                path,
                "-outFile",
                temporary,
                "-selfSign",
                "1",
            ],
            check=True,
            timeout=60,
        )
        sections = subprocess.run(
            [readelf, "-SW", temporary],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
        if sections.count(".codesign") != 1:
            raise ConanException("signed consumer has invalid .codesign: {}".format(path))
        os.chmod(temporary, (os.stat(path).st_mode & 0o777) | 0o055)
        os.replace(temporary, path)
