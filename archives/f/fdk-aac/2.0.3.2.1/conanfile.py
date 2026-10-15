from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
import os


class FdkAacConan(ConanFile):
    name = "fdk-aac"
    version = "2.0.3.2.1"
    description = "A standalone Fraunhofer FDK AAC codec library"
    license = "FDK-AAC"
    homepage = "https://sourceforge.net/projects/opencore-amr/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        # conandata sources 为有序候选组列表(每组 url+sha256 自洽):
        # GitHub tag archive 与 SourceForge 官方发行包字节流不同,无法共用
        # 校验值,故逐组尝试,任一组下载+校验成功即用,全部失败再抛错。
        last_error = None
        for sources in self.conan_data["sources"]:
            try:
                get(self, **sources, strip_root=True)
                return
            except Exception as e:
                last_error = e
                self.output.warning(f"source URL 组失败,尝试下一组: {e}")
        raise ConanException(f"所有源 URL 均失败: {last_error}")

    def generate(self):
        self.output.info(f"DEBUG generator conf = {self.conf.get('tools.cmake.cmaketoolchain:generator')!r}")
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # E092: CMake 不识别 HarmonyOS 平台(无 Platform/OHOS module),configure
        # 阶段编译器探测失败(CMakeLists.txt:46 project)。OHOS 基于 Linux 内核,
        # 按 E092 rec_approach 让 CMake 以 Linux 平台生成(aarch64 由 profile
        # 传递,标准 ohpcd ohos-aarch64 profile 下可正确 configure)。
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = str(self.settings.arch)
        # OHOS 真机/CI Worker 的 make 执行 /bin/sh 受限(Permission denied),
        # 强制 Ninja 生成器(ninja 由 profile buildenv PATH 提供,不经 shell)。
        self.conf.define("tools.cmake.cmaketoolchain:generator", "Ninja")
        # 构建上游自检程序 aac-enc(install)与 test-encode-decode(留在构建树,
        # 不 install——test_package 把上游源 vendor 进包内重新编译)。
        tc.variables["BUILD_PROGRAMS"] = "ON"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        # 真机 OHOS 沙箱进程配额有限:ninja 默认并行度(cores+2,20 核实测 ≈45
        # 活进程)触发 posix_spawn EAGAIN 中道崩殂,必须限并发。
        cmake.build(cli_args=["--parallel", "8"])
        self._run_upstream_official_tests()

    def _run_upstream_official_tests(self):
        """上游官方测试套件执行（CI L1 门禁：build() 内必须真实运行上游测试）。

        官方 test-encode-decode（BUILD_PROGRAMS=ON 构建产物）对确定性合成
        wav 跑全模式矩阵（mono 11 模式：AAC-LC/HE-AAC/AAC-LD/AAC-ELD+VBR），
        上游验收语义：退出码 = failures 数（各模式解码 avg_diff 超阈值即计
        failure），并输出聚合 encode/decode SHA-1 哈希行（与官方 run-test.sh
        同口径）。完整双 wav fixture 位元比对（按架构分流）见 test_package
        三阶段测试。
        """
        import glob as _glob
        import re
        import struct
        import subprocess
        import wave as _wave

        candidates = [
            c for c in _glob.glob(os.path.join(self.build_folder, "**", "test-encode-decode"), recursive=True)
            if os.path.isfile(c) and os.access(c, os.X_OK)
        ]
        if not candidates:
            raise ConanException("上游官方测试工具 test-encode-decode 未构建")
        tool = candidates[0]

        # 确定性合成 wav:441Hz 正弦表(编译期常量,与 math.sin/libm 实现无关,
        # 同架构跨平台位元可复现),2s@44.1kHz mono,16-bit PCM
        rate, secs = 44100, 2
        sine_tab = [
            0, 1005, 2005, 2998, 3979, 4944, 5890, 6812, 7708, 8573,
            9405, 10199, 10953, 11663, 12328, 12944, 13509, 14021, 14477, 14876,
            15217, 15497, 15717, 15874, 15968, 16000, 15968, 15874, 15717, 15497,
            15217, 14876, 14477, 14021, 13509, 12944, 12328, 11663, 10953, 10199,
            9405, 8573, 7708, 6812, 5890, 4944, 3979, 2998, 2005, 1005,
            0, -1005, -2005, -2998, -3979, -4944, -5890, -6812, -7708, -8573,
            -9405, -10199, -10953, -11663, -12328, -12944, -13509, -14021, -14477, -14876,
            -15217, -15497, -15717, -15874, -15968, -16000, -15968, -15874, -15717, -15497,
            -15217, -14876, -14477, -14021, -13509, -12944, -12328, -11663, -10953, -10199,
            -9405, -8573, -7708, -6812, -5890, -4944, -3979, -2998, -2005, -1005,
        ]
        frames = bytearray()
        for i in range(rate * secs):
            frames += struct.pack("<h", sine_tab[i % 100])
        wav_path = os.path.join(self.build_folder, "ci-upstream-smoke.wav")
        wav = _wave.open(wav_path, "wb")
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(bytes(frames))
        wav.close()

        # 工具链接共享库时构建树内解析(BUILD_SHARED_LIBS=ON)
        env = dict(os.environ)
        lib_dirs = set()
        for so in _glob.glob(os.path.join(self.build_folder, "**", "libfdk-aac.so*"), recursive=True):
            lib_dirs.add(os.path.dirname(so))
        if lib_dirs:
            env["LD_LIBRARY_PATH"] = os.pathsep.join(
                list(lib_dirs) + [env.get("LD_LIBRARY_PATH", "")]).rstrip(os.pathsep)

        self.output.info("上游官方测试: test-encode-decode 全模式矩阵(mono 11 模式, 合成 wav)")
        result = subprocess.run(
            [tool, wav_path], capture_output=True, text=True,
            cwd=os.path.dirname(tool), env=env, timeout=1800)
        combined = (result.stdout or "") + "\n" + (result.stderr or "")
        tail = combined[-1800:]
        self.output.info(f"上游测试输出尾部:\n{tail}")
        if result.returncode != 0:
            raise ConanException(f"上游官方测试失败: 退出码 {result.returncode} (=failures 数)")
        if "0 failures" not in combined:
            raise ConanException("上游官方测试输出缺少 '0 failures' 验收行")
        hash_lines = re.findall(r"^(?:encode|decode) hash: [0-9a-f]{40}$", combined, re.M)
        if len(hash_lines) != 2:
            raise ConanException(f"上游官方测试哈希行形状异常: {len(hash_lines)} 行(应为 2)")

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "NOTICE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["fdk-aac"]
