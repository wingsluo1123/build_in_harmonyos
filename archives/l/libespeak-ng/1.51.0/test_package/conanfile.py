import os
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibespeakngTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        # E1031b：与主配方 build()/package() 同源——CI worker 上 make jobserver
        # 用 mkfifo 创建管道被拒（Operation not permitted），且并行 fork 触发
        # 进程数超限（posix_spawn/fork EAGAIN，资源耗尽）。强制 -j1 单线程构建。
        cmake.build(build_tool_args=["-j1"])

    def test(self):
        # R34：实质调用被测包 —— espeak_Initialize/espeak_Synth 合成音频，
        # 通过 SynthCallback 收集 PCM 并写盘校验；另有 test 基础初始化测试。
        # espeak-ng 运行期需要 espeak-ng-data（112 个语言字典 + 音素数据），
        # 显式设置 ESPEAK_DATA_PATH 指向包内数据目录，保证 CI 干净环境可用。
        pkg = self.dependencies["libespeak-ng"].package_folder
        data_path = os.path.join(pkg, "share", "espeak-ng-data")
        if not os.path.isdir(data_path):
            raise SystemExit(
                f"FATAL: espeak-ng-data not found at {data_path}")
        bindir = self.cpp.build.bindirs[0]
        self.run(f"ESPEAK_DATA_PATH={data_path} "
                 f"{os.path.join(bindir, 'test_basic')}",
                 env="conanrun")
        self.run(
            f"ESPEAK_DATA_PATH={data_path} "
            f"{os.path.join(bindir, 'test_libespeak-ng')}",
            env="conanrun")
        # CLI 端到端消费者用例（鸿蒙特有测试，R34 实质执行）：真实调用包内
        # espeak-ng 命令行工具合成 WAV 并校验（RIFF/WAVE 魔数 + 非空），
        # 验证命令行解析→引擎初始化→语音合成→文件写出完整链路。
        # 依赖包 lib 目录用于 LD_LIBRARY_PATH（CLI 动态链接 libespeak-ng.so）。
        pkg_bin = os.path.join(pkg, "bin")
        pkg_lib = os.path.join(pkg, "lib")
        self.run(f"sh {os.path.join(self.source_folder, 'test_cli.sh')} "
                 f"{pkg_bin} {data_path} {pkg_lib}",
                 env="conanrun")