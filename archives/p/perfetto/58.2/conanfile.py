import os
import shutil
import textwrap

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import build_jobs
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    mkdir,
    save,
)

required_conan_version = ">=2.0"


class PerfettoConan(ConanFile):
    name = "perfetto"
    version = "58.2"
    # 本包既产出 CLI 工具，也产出 libperfetto.so / 公共头供消费者链接。
    # 注意：package_type="application" 会让 conan 清空 cpp_info.libs/includedirs，
    # 导致 CMakeDeps 不导出头文件路径；故声明为 shared-library。
    package_type = "shared-library"
    description = (
        "System profiling, app tracing and trace analysis: Perfetto trace processor, "
        "traced service, tracing SDK and CLI, adapted to HarmonyOS PC (OHOS aarch64)."
    )
    license = "Apache-2.0"
    url = "https://github.com/google/perfetto"
    homepage = "https://perfetto.dev"
    topics = ("tracing", "profiling", "trace-processor", "gn", "ninja")

    settings = "os", "compiler", "build_type", "arch"

    # 说明：构建用 GN（上游 standalone 方式），同时打包 libperfetto + public headers
    # 供消费者链接使用。
    #
    # with_tests：是否额外构建上游测试二进制（6 个 *_unittests + benchmarks +
    # integrationtests + smoke）。**默认关**——CI 只跑 conan create + test_package，
    # 不运行单测，而这些二进制合计 ~1.6 GB，编译+链接占整条流水线的大头，会顶到
    # CI 默认 3600 s 的构建超时。本地复现全量上游测试用：
    #   conan create . -o "&:with_tests=True"
    options = {"with_tests": [True, False]}
    default_options = {"with_tests": False}

    # 产品件（零裁剪：trace_processor / traced / perfetto CLI 核心组件全开）
    _PRODUCT_TARGETS = [
        "libperfetto.so",
        "libperfetto_client_experimental.a",
        "trace_processor_shell",
        "tracebox",
        "traceconv",
        "perfetto",
        "traced",
        "traced_probes",
        "protoc",
    ]

    # 上游测试二进制（with_tests=True 时构建；宿主侧全量实测见 notes.md §7）
    _TEST_TARGETS = [
        "perfetto_unittests",
        "perfetto_base_unittests",
        "perfetto_misc_unittests",
        "perfetto_profiling_unittests",
        "perfetto_trace_processor_unittests",
        "perfetto_tracing_unittests",
        "trace_processor_minimal_smoke_tests",
        "perfetto_benchmarks",
        "perfetto_integrationtests",
    ]

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # CI worker 的 PATH 不含 hnp/bin，裸名探 ninja 会失败；用 tool_requires 提供绝对路径。
        self.tool_requires("ninja/1.13.2")

    def validate(self):
        if self.settings.os != "OHOS":
            raise ConanInvalidConfiguration(
                "perfetto 58.2 recipe 仅支持 OHOS (HarmonyOS PC / aarch64)"
            )

    # ------------------------------------------------------------------ source
    def _filename(self, name, fmt, explicit=""):
        """codeload 的 URL 末段是 SHA（无扩展名），必须显式给出带扩展名的文件名，
        否则 conan 的 get() 无法识别归档格式。"""
        if explicit:
            return explicit
        ext = {"tar.gz": ".tar.gz", "zip": ".zip", "tgz": ".tgz"}.get(fmt, "")
        return "".join(c if c.isalnum() or c in "._-" else "_" for c in name) + ext

    def source(self):
        # 注意：conandata.yml 里的 filename/tar_format 供人读与校验；
        # conan 的 get() 只认 url/sha256/filename/strip_root，这里显式传参。
        src = self.conan_data["sources"]
        get(self, url=src["url"], sha256=src.get("sha256", ""),
            filename=self._filename("perfetto", src.get("tar_format", "tar.gz"),
                                    src.get("filename", "")),
            destination=self.source_folder, strip_root=True)

        # GN 工具链：上游不 vendor 二进制，预编译 gn 为 x86/glibc 且无 .codesign，
        # 故按上游 install-build-deps 指定的 revision 从源码自举。
        gn = self.conan_data["build_tools"]["gn"]
        get(self, url=gn["url"], sha256=gn.get("sha256", ""),
            filename=self._filename("gn", gn.get("tar_format", "tar.gz"),
                                    gn.get("filename", "")),
            destination=os.path.join(self.source_folder, "_gn"), strip_root=True)

        # perfetto standalone 构建所需的 buildtools/ 第三方源码
        for dep in self.conan_data["buildtools"]:
            dst = os.path.join(self.source_folder, "buildtools", dep["dst"])
            mkdir(self, dst)
            get(self, url=dep["url"], sha256=dep.get("sha256", ""),
                filename=self._filename(dep["dst"], dep.get("tar_format", "tar.gz"),
                                        dep.get("filename", "")),
                destination=dst, strip_root=dep.get("strip_root", True))

        apply_conandata_patches(self)

    # ------------------------------------------------------------------ helpers
    def _toolchain(self):
        """返回 (cc, cxx, ar) 绝对路径，取自 profile 的 compiler_executables。"""
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c") or shutil.which("clang") or "clang"
        cxx = compilers.get("cpp") or shutil.which("clang++") or "clang++"
        # OHOS python subprocess 不做 PATH 搜索，gn 的 ar 必须给绝对路径。
        ar = os.path.join(os.path.dirname(cc), "llvm-ar")
        if not os.path.exists(ar):
            ar = shutil.which("llvm-ar") or shutil.which("ar") or "ar"
        return cc, cxx, ar

    def _ninja(self):
        ninja = os.path.join(self.dependencies.build["ninja"].cpp_info.bindir, "ninja")
        return ninja if os.path.exists(ninja) else (shutil.which("ninja") or "ninja")

    def _gn_args(self):
        cc, cxx, ar = self._toolchain()
        return " ".join(
            [
                "is_debug=false",
                # 用 OHOS 系统 clang（非上游 hermetic clang）：
                "is_system_compiler=true",
                "is_hermetic_clang=false",  # 上游为系统编译器保留的配置（无 -Weverything/-Werror）
                # 上游把 linux/arm64 当成 "x64 主机交叉编 arm64"（默认 Debian sysroot），OHOS 上清空：
                'target_triplet=""',
                'sysroot=""',
                # OHOS sysroot 自带 libc++，无需重建上游 vendored libc++：
                "use_custom_libcxx=false",
                # 跳过 install-build-deps 产物校验（依赖已由 source() 供给）：
                "skip_buildtools_check=true",
                # OHOS sysroot 自带 zlib，取代不可得的 chromium zlib fork：
                "perfetto_use_system_zlib=true",
                # OHOS 上 strip 会破坏 .codesign，且 hermetic llvm-objcopy 不存在：
                'strip=""',
                f'ar="{ar}"',
            ]
        )

    # ------------------------------------------------------------------- build
    def generate(self):
        # gn 的 is_system_compiler=true 路径从环境变量读 CC/CXX；gen.py 也用 CXX。
        # OHOS python subprocess 不做 PATH 搜索，ar 必须是绝对路径。
        cc, cxx, ar = self._toolchain()
        env = Environment()
        env.define("CC", cc)
        env.define("CXX", cxx)
        env.define("AR", ar)
        env.vars(self).save_script("conanbuild_ccenv")

    def build(self):
        ninja = self._ninja()
        envs = ["conanbuild", "conanbuild_ccenv"]

        # 1) 自举 GN（OHOS clang 链接期自动加 .codesign，产物可直接执行）
        gn_dir = os.path.join(self.source_folder, "_gn")
        self.run("python3 build/gen.py --no-last-commit-position",
                 cwd=gn_dir, env=envs)
        # gen.py 无 git 元数据时不会生成该头，需手工补（否则 scope_per_file_provider.cc 报错）
        save(
            self,
            os.path.join(gn_dir, "out", "last_commit_position.h"),
            textwrap.dedent(
                """\
                // Generated by build/gen.py.
                #ifndef OUT_LAST_COMMIT_POSITION_H_
                #define OUT_LAST_COMMIT_POSITION_H_
                #define LAST_COMMIT_POSITION_NUM 0
                #define LAST_COMMIT_POSITION "0 (unknown)"
                #endif  // OUT_LAST_COMMIT_POSITION_H_
                """
            ),
        )
        self.run(f'"{ninja}" -C out', cwd=gn_dir, env=envs)
        gn = os.path.join(gn_dir, "out", "gn")

        # 2) 生成 perfetto 构建文件（--args 用单引号包裹，避免 shell 吞掉内层 ""）
        self.run(f"\"{gn}\" gen out/ohos '--args={self._gn_args()}'",
                 cwd=self.source_folder, env=envs)

        # 3) 构建：产品件（零裁剪）+ 可选的上游测试二进制（默认不建，见 with_tests 说明）
        jobs = min(build_jobs(self), 16)
        targets = list(self._PRODUCT_TARGETS)
        if self.options.with_tests:
            targets += self._TEST_TARGETS
        self.run(f'"{ninja}" -C out/ohos -j{jobs} ' + " ".join(targets),
                 cwd=self.source_folder, env=envs)

    # ----------------------------------------------------------------- package
    def package(self):
        od = os.path.join(self.build_folder, "out", "ohos")
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

        for exe in ("trace_processor_shell", "tracebox", "traceconv", "perfetto",
                    "traced", "traced_probes", "protoc"):
            copy(self, exe, src=od, dst=os.path.join(self.package_folder, "bin"))

        copy(self, "*.so", src=od, dst=os.path.join(self.package_folder, "lib"))
        copy(self, "*.a", src=od, dst=os.path.join(self.package_folder, "lib"))
        # perfetto 的可执行文件以 rpath `$ORIGIN/.` 链接 libperfetto.so（上游 standalone 是
        # 扁平输出目录）。为让 bin/ 下的 CLI 开箱即用，除 lib/ 外再在 bin/ 放一份。
        copy(self, "libperfetto.so", src=od, dst=os.path.join(self.package_folder, "bin"))

        copy(self, "*.h", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"), keep_path=True)
        # 公共头 perfetto/base/build_config.h 会 include 生成头 perfetto_build_flags.h
        # （上游由 -Igen/build_config 提供），需一并打包供消费者编译。
        copy(self, "*.h",
             src=os.path.join(od, "gen", "build_config"),
             dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libs = ["perfetto"]
