#!/usr/bin/env python3
"""Conan recipe — genometools 1.6.2 (upstream tag v1.6.2, hand-written Makefile).

GenomeTools 是 LTRsift 的核心依赖（ltrsift 链接 -lgenometools 并包含
genometools.h）。

上游构建契约（手写 GNUmakefile，无 configure/CMake）：
  - 自带全部 external 依赖（zlib/expat/lua/bzip2/samtools/sqlite/tre），
    默认 `useshared=no` 直接静态编入 libgenometools —— 因此本配方
    **没有任何 conan requirements**（W0 结论：零外部依赖）。
  - `cairo=no`：关掉 annotationsketch 绘图子系统（GOTAGS/-tags cairo），
    ltrsift 只用 core/extended/ltr API，不需要 gt-sketch；这样连
    pkg-config 探测 pango/cairo 的路径都不进。
  - `64bit=yes`：显式 64bit，绕过 uname -m 探测（OHOS 目标非 x86_64）。
  - `sharedlib=yes`（默认）：产出 lib/libgenometools.so + lib/libgenometools.a
    + bin/gt。
  - CC/CXX 默认 gcc/g++，OHOS 必须显式传 clang/clang++。
  - 上游测试入口 1：`bin/gt -test`（C 内建单元测试，无外部依赖）；
    入口 2：testsuite/（Ruby 驱动，testsuite.rb），设备无 ruby —— 如实登记。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

_SOURCE_URL = "https://github.com/genometools/genometools/archive/refs/tags/v1.6.2.tar.gz"
_SOURCE_SHA256 = "974825ddc42602bdce3d5fbe2b6e2726e7a35e81b532a0dc236f6e375d18adac"


class GenometoolsConan(ConanFile):
    name = "genometools"
    version = "1.6.2"
    description = ("GenomeTools — a comprehensive library of genome analysis "
                   "tools (gt CLI plus the libgenometools shared library)")
    license = "ISC"
    homepage = "https://github.com/genometools/genometools"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        # 上游 default 同时产出 .a 与 .so；不提供纯 static 变体开关，
        # 静态库只是共享构建的副产物 —— 统一只发 shared 形态。
        if not self.options.shared:
            raise ConanInvalidConfiguration(
                "genometools/1.6.2 is shared-only in this recipe: upstream "
                "make builds the static archive as part of the shared build")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"Unsupported OS: {self.settings.os}")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, url=_SOURCE_URL, sha256=_SOURCE_SHA256, strip_root=True)
        # HMDFS 无符号链接：上游 tarball 内 src/external/samtools-0.1.18/samtools/
        # 是一组指回本目录的符号链接头文件（<samtools/sam.h> 引用面），
        # 在 HMDFS 上解包后为空目录。此处用真实文件镜像兜底（幂等：
        # Linux 正常解包时 sam.h 已存在，跳过）。
        st_dir = os.path.join(self.source_folder, "src", "external",
                              "samtools-0.1.18")
        sam_dir = os.path.join(st_dir, "samtools")
        sam_h = os.path.join(sam_dir, "sam.h")
        if not os.path.isfile(sam_h):
            os.makedirs(sam_dir, exist_ok=True)
            for name in os.listdir(st_dir):
                if name.endswith(".h"):
                    shutil.copy2(os.path.join(st_dir, name),
                                 os.path.join(sam_dir, name))

    # ------------------------------------------------------------------ #
    # build
    # ------------------------------------------------------------------ #
    def _compiler(self, lang):
        conf = self.conf.get("tools.build:compiler_executables", default=None)
        if isinstance(conf, dict):
            return conf.get(lang) or conf.get("cpp") or ("clang" if lang == "c" else "clang++")
        return "clang" if lang == "c" else "clang++"

    def _jobs(self):
        # CI worker（共享 OHOS 设备）进程数受限：-j2 时 make 的并行 shell
        # 会成批 "can't fork - try again"（EAGAIN）→ Error 127。
        # 串行 -j1 换稳定；构建耗时换 CI 可靠通过。
        # （make jobserver mkfifo 的 Operation not permitted 是非致命告警，
        #   见 opencsg-1.8.2-make-jobserver-mkfifo-not-permitted 先例。）
        return self.conf.get("tools.build:jobs", default=1, check_type=int) or 1

    def build(self):
        apply_conandata_patches(self)
        # EXP_LDFLAGS 同时作用于 libgenometools.so 与 bin/gt 的链接：
        # bin/gt 在安装树位于 bin/、库在 lib/，故注入 $ORIGIN/../lib，
        # 裸环境（无 LD_LIBRARY_PATH）可执行是 L2 的判据。
        # --allow-multiple-definition：上游把 expat 对象同时经目录通配
        # （LIBGENOMETOOLS_OBJ）与 lib/libexpat.a（ADDITIONAL_SO_DEPS）喂给
        # 链接器；GNU ld 对「对象+归档成员重复」取对象不报错，lld 直接判重。
        # 此开关只是恢复 GNU ld 语义，符号来源唯一（同一份 xmlparse.c）。
        # TMPDIR/HOME 用内联变量收敛到构建目录（平台 /tmp 只读，脚本可能
        # 产生临时文件；不使用 Environment()/generate() —— 设备端 conan 的
        # EnvVars 无 define 方法，版本 API 有差异）。
        self.run(
            'TMPDIR="{tmp}" HOME="{tmp}" '
            'make -j{jobs} CC="{cc}" CXX="{cxx}" 64bit=yes cairo=no sharedlib=yes '
            'errorcheck=no CFLAGS="-O3" '
            'LDFLAGS="-Wl,-rpath,$ORIGIN/../lib -Wl,-soname,libgenometools.so.1 '
            '-Wl,--allow-multiple-definition" all'.format(
                tmp=self.build_folder,
                jobs=self._jobs(),
                cc=self._compiler("c"),
                cxx=self._compiler("cpp"),
            ),
            cwd=self.source_folder,
        )
        # 上游测试入口 1：C 内建单元测试（无 ruby 等外部依赖）。
        self.run(
            'LD_LIBRARY_PATH="{src}/lib" ./bin/gt -test'.format(
                src=self.source_folder),
            cwd=self.source_folder,
        )
        # 上游测试入口 2（testsuite/*.rb，Ruby 驱动）在 OHOS 设备无 ruby
        # 解释器，无法执行 —— 如实登记于 manifest/notes，不计为通过。

    # ------------------------------------------------------------------ #
    # package
    # ------------------------------------------------------------------ #
    def package(self):
        src = self.source_folder
        copy(self, "LICENSE", src, os.path.join(self.package_folder, "licenses"))
        for doc in ("README", "README.md", "CHANGELOG", "VERSION", "INSTALL"):
            copy(self, doc, src, os.path.join(self.package_folder,
                                              "share", "genometools", "doc"))

        libdir = os.path.join(self.package_folder, "lib")
        bindir = os.path.join(self.package_folder, "bin")
        incdir = os.path.join(self.package_folder, "include", "genometools")
        os.makedirs(libdir, exist_ok=True)
        os.makedirs(bindir, exist_ok=True)

        # 库：上游无版本化产物，但 L5a 门禁要求 DT_SONAME——链接期已注入
        # -soname,libgenometools.so.1；这里落盘为 libgenometools.so.1，
        # libgenometools.so 优先 symlink（HMDFS 无 symlink 时退化为实体副本，
        # 两个文件都带同样的 SONAME，L5a 扫描均通过）。
        built_so = os.path.join(src, "lib", "libgenometools.so")
        if not os.path.isfile(built_so):
            raise ConanException("upstream build did not produce lib/libgenometools.so")
        copy(self, "libgenometools.so", os.path.join(src, "lib"), libdir,
             keep_path=False)
        installed_so1 = os.path.join(libdir, "libgenometools.so.1")
        os.rename(os.path.join(libdir, "libgenometools.so"), installed_so1)
        os.chmod(installed_so1, 0o755)
        link = os.path.join(libdir, "libgenometools.so")
        if os.path.lexists(link):
            os.remove(link)
        try:
            os.symlink("libgenometools.so.1", link)
        except OSError:
            shutil.copy2(installed_so1, link)
        # 静态副产物（shared 构建自带），一并交付。
        copy(self, "libgenometools.a", os.path.join(src, "lib"), libdir,
             keep_path=False)

        # CLI：bin/gt。
        gtbin = os.path.join(bindir, "gt")
        copy(self, "gt", os.path.join(src, "bin"), bindir, keep_path=False)
        if not os.path.isfile(gtbin):
            raise ConanException("upstream build did not produce bin/gt")
        os.chmod(gtbin, 0o755)

        # 头文件：与上游 install 布局一致 —— <prefix>/include/genometools/ 下
        # core/extended/ltr/... 的 *_api.h + genometools.h + gt_config.h。
        # 注意 annotationsketch 头必须带：genometools.h（all-in-one）无条件
        # include 它们，与 cairo=no 只裁实现不冲突（消费者不调用即不可达）。
        for sub in ("core", "extended", "ltr", "match", "mgth", "gtlua",
                    "annotationsketch"):
            copy(self, "*_api.h", os.path.join(src, "src", sub),
                 os.path.join(incdir, sub), keep_path=False)
        copy(self, "genometools.h", os.path.join(src, "src"), incdir, keep_path=False)
        gt_config = os.path.join(src, "obj", "gt_config.h")
        if not os.path.isfile(gt_config):
            raise ConanException("obj/gt_config.h missing (build incomplete)")
        copy(self, "gt_config.h", os.path.join(src, "obj"), incdir, keep_path=False)

        # 运行数据：gtdata（部分 gt 工具需要，体积可接受，一并打包）。
        copy(self, "*", os.path.join(src, "gtdata"),
             os.path.join(self.package_folder, "share", "genometools", "gtdata"),
             keep_path=True)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "genometools")
        self.cpp_info.set_property("cmake_target_name", "genometools::genometools")
        self.cpp_info.set_property("pkg_config_name", "genometools")
        self.cpp_info.libs = ["genometools"]
        # cairo=no 构建时，genometools.h 的 AnnotationSketch 段靠
        # #ifndef WITHOUT_CAIRO 守卫（上游约定由消费者提供该宏），
        # 不定义会拉进 <cairo.h>。
        self.cpp_info.defines = ["WITHOUT_CAIRO"]
        # ltrsift 消费契约：-I<gt>/include/genometools + #include "genometools.h"
        self.cpp_info.includedirs = ["include/genometools"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        # 静态编入的外部库符号（zlib/expat/bz2/lua...）都在 libgenometools.so
        # 内部，无传递链接需求；不伪造额外 libs。
        self.cpp_info.system_libs = ["m", "pthread"]
