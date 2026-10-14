#!/usr/bin/env python3
"""Conan recipe — mesa 24.3.4.1.1（Mesa 3D 图形库，HarmonyOS PC 适配）

Conan package 24.3.4.1.1 tracks upstream Mesa 24.3.4 and builds the
OSMesa software-rendering target for desktop OpenGL compatibility.
OHOS 适配点：
- -fno-emulated-tls（OHOS 工具链默认 emutls 会污染 glapi 导出符号）
- 平台 symbols 白名单（bin/symbols-check.py 已加 HarmonyOS）
- u_process.c /proc/self/exe 进程名（OHOS 无 program_invocation_name）
- memstream close 前 fflush（OHOS open_memstream 只在 fflush 刷新）
"""
from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import PkgConfigDeps
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.layout import basic_layout
import os
import shutil


class MesaConan(ConanFile):
    name = "mesa"
    version = "24.3.4.1.1.1"
    description = "mesa 24.3.4.1.1.1 — Mesa 3D 图形库（HarmonyOS PC, OSMesa/softpipe/GBM/EGL/GLES/GLX, X11 window 平台）"
    license = "MIT"
    homepage = "https://www.mesa3d.org/"
    url = "https://gitlab.freedesktop.org/mesa/mesa"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    # ohos_adapt_test.c 是鸿蒙专项测试新增源码，随配方导出并在 source()
    # 阶段复制进包内源码树，配合 patches/0003 的 meson.build 目标引用
    exports_sources = "src_additions/*"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # expat：mesa xmlconfig/drirc 解析必需
        self.requires("expat/2.8.2.1.1")
        # libdrm：GBM 后端硬依赖（-Dgbm=enabled 需要 libdrm 头文件/库）
        self.requires("libdrm/2.4.133")
        # llvm：llvmpipe 软件渲染器依赖（r24 全功能扩展；llvm/20.1.0 在 ohpcd
        # registry 有预编译二进制，同 ldc/spirv-llvm-translator 消费先例）。
        # R03：llvm 改 visible=False——CMakeDeps 对 llama（cmake_find_mode=none，
        # 无 llama-config.cmake）仍把可见 requires 聚合进 mesa_DEPS_TARGET 引用
        # llama::llvm（target 未定义，消费者 find_package(mesa) 失败——第 28 次
        # 实证）。visible=False 使 llama 完全脱离 CMakeDeps 依赖列表；
        # libgallium/libOSMesa NEEDED libLLVM.so.20.1 的运行时路径由 generate()
        # 写入 generators_folder 文件、package_info() 读取补进 mesa runenv_info
        #（generators_folder 跨 generate/package_info 稳定，规避实例属性不存活）。
        self.requires("llvm/20.1.0", visible=False)
        # r38（24.3.4.1.1.1）：X11 window 平台/GLX 启用所需的 X11 客户端依赖
        # （仅客户端库，禁止 Xvfb 服务器端依赖混入）。libx11 提供 Xlib/X11-xcb
        # 头与 libX11/libX11-xcb，libxcb 提供 X protocol 绑定，xorgproto 提供
        # X11 协议/扩展头（mesa x11 platform 与 GLX 的 meson dependency('x11')
        # /dependency('xcb') 经 PkgConfigDeps 生成的 x11.pc/xcb.pc 解析）。
        self.requires("libx11/6.4.0", transitive_headers=True, transitive_libs=True)
        self.requires("libxcb/1.16", transitive_headers=True, transitive_libs=True)
        self.requires("xorgproto/2025.1", transitive_headers=True)
        # libxext：mesa x11 平台/GLX 的 dependency('xext') 依赖（meson.build
        # xext 探测失败即 configure 中断——第三次构建实证），libxext/6.4.0
        # pkg_config_name=xext，actiona 先例同版本引用。
        self.requires("libxext/6.4.0", transitive_headers=True, transitive_libs=True)
        # glx=dri 完整依赖链（meson.build with_glx=='dri' 分支，第四次构建实证
        # xfixes 缺失中断）：xfixes（libxfixes）、xshmfence（libxshmfence，
        # with_dri_platform=='drm' 必需）、xxf86vm（with_glx_direct 启用时）。
        # xcb-glx/xcb-shm/xcb-dri2/xcb-dri3/xcb-present/xcb-sync 由 libxcb
        # EXTENSION_LIBS 组件提供（PkgConfigDeps 生成 xcb-*.pc）；
        # glproto/dri2proto 由 xorgproto pc 模块提供。
        self.requires("libxfixes/6.1.0", transitive_headers=True, transitive_libs=True)
        self.requires("libxshmfence/1.3.3", transitive_headers=True, transitive_libs=True)
        self.requires("libxxf86vm/1.1.5", transitive_headers=True, transitive_libs=True)
        # glproto：mesa meson dependency('glproto', version: '>=1.4.14')
        # （glx=dri 分支），独立 header 包，PkgConfigDeps 生成 glproto.pc
        # 供探测（xorgproto 的 share/pkgconfig 在 conanbuild 环境探测不到，
        # 第六次构建实证，改为显式 requires）。
        self.requires("glproto/1.4.17", transitive_headers=True)
        # libxrandr：mesa meson dependency('xrandr', version: '>=1.3')
        # （with_xlib_lease 分支，第九次构建实证 xrandr 缺失中断），
        # pkg_config_name=xrandr，ohpcd 已发布。
        self.requires("libxrandr/1.5.5", transitive_headers=True, transitive_libs=True)

    def build_requirements(self):
        # Mesa's OSMesa + softpipe build still generates Gallium/OpenGL
        # parser sources during Meson configure. Keep these tools explicit so
        # the recipe does not depend on an undocumented device PATH.
        self.tool_requires("bison/3.8.2")
        self.tool_requires("flex/2.6.4.2")
        # flex binaries from the artifact store may retain the builder's
        # absolute M4 path; resolve the macro processor in this graph.
        self.tool_requires("m4/1.4.19")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # 将导出的鸿蒙专项测试源码放入包内源码树，供 patches/0003 引用的
        # ohos_adapt_test 目标编译。R02 实证：export_sources_folder 解包结构为
        # <es>/src_additions/gallium/tests/trivial/（exports_sources="src_additions/*"
        # 保留顶层目录名），此前 src 写为 export_sources_folder/gallium/tests/trivial
        # 缺少 src_additions 段——R01 build-tests=false 时 trivial 目录未实例化
        # 不报错，R02 build-tests=true 使 meson 检查该源文件而失败，已修正。
        copy(self, "ohos_adapt_test.c",
             src=os.path.join(self.export_sources_folder, "src_additions", "gallium", "tests", "trivial"),
             dst=os.path.join(self.source_folder, "src", "gallium", "tests", "trivial"),
             keep_path=False)

    def generate(self):
        # r24：llvmpipe 需要 LLVM。meson 以 config-tool 探 llvm-config，且其运行
        # 环境是 conanbuild（不继承 build() 内 os.environ 改动）。通过
        # buildenv_info 把依赖 llvm/20.1.0 包的 bin 前置注入 conanbuild PATH，
        # 保证 meson 探测到 20.1.0 而非系统 15.0.4（ldc/spirv-llvm-translator 同款）。
        if "llvm" in self.dependencies:
            llvm_pkg = self.dependencies["llvm"]
            llvm_bin = os.path.join(llvm_pkg.package_folder, "bin")
            if os.path.isdir(llvm_bin):
                self.buildenv_info.prepend_path("PATH", llvm_bin)
            # R03：llvm visible=False 后其 runenv_info 不自动传播；libgallium/
            # libOSMesa NEEDED libLLVM.so.20.1（运行时动态加载）。generate()
            # 阶段 package_folder 可用（package_info 阶段 visible=False 依赖
            # package_folder 为 None——第 5 次实证），把 llama lib 路径写入
            # generators_folder 文件供 package_info() 读取（generators_folder
            # 跨阶段稳定，规避实例属性不存活——第 22/24 次实证）。
            llvm_lib = os.path.join(llvm_pkg.package_folder, "lib")
            if os.path.isdir(llvm_lib):
                # R03：把 llama lib 路径写入 build-release/conan 供本包
                # package()/package_info() 读取；也写入 source_folder 根以跨
                # generate/package 阶段稳定（generators_folder 在 test_package
                # 上下文中为 None——第 30 次实证读取失败）。
                try:
                    with open(os.path.join(self.generators_folder, "mesa_llvm_lib_dir"), "w") as _f:
                        _f.write(llvm_lib)
                except Exception:
                    pass
            # PkgConfigDeps：expat/libdrm 的 .pc 进入 generators 目录，meson 的
            # pkg-config 探测才能找到（-Dgbm=enabled 使 libdrm 成为 required 依赖）
        PkgConfigDeps(self).generate()
        # r38（24.3.4.1.1.1）：xorgproto 包内 share/pkgconfig 含 dri2proto.pc
        # 等 X11 协议 pc（PC_MODULES 模板生成），但 meson 探测时 PKG_CONFIG_PATH
        # 只含 generators 目录（meson-log 实证 env[PKG_CONFIG_PATH] 仅
        # build-release/conan；glproto 因显式 requires 生成于该目录故可解析，
        # dri2proto 探测失败）。把 xorgproto 的 dri2proto.pc 复制进 generators
        # 目录即可命中 pkg-config 探测（dri2proto >=2.8 满足）。
        if "xorgproto" in self.dependencies:
            xgproto_pc = os.path.join(
                self.dependencies["xorgproto"].package_folder, "share", "pkgconfig"
            )
            for pc_name in ("dri2proto.pc", "glproto.pc"):
                src = os.path.join(xgproto_pc, pc_name)
                if os.path.isfile(src):
                    shutil.copy2(
                        src,
                        os.path.join(self.generators_folder, pc_name),
                    )
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        # r38（24.3.4.1.1.1）：启用 X11 window 平台（EGL_MESA_platform_x11 /
        # EGL_EXT_platform_x11 / KHR_platform_x11 扩展、eglChooseConfig 返回
        # WINDOW_BIT 配置）+ GLX（libGL.so.1）。mesa 24.3.4 的 platforms 选项
        # 只接受窗口系统平台（x11/wayland/haiku/android/windows/macos）——
        # surfaceless 是 EGL 在无窗口平台时内建自动启用（platforms 不含
        # surfaceless 值也始终可用），drm 路径由 gbm=enabled/dri 提供而非
        # platforms 值，故 platforms 设为 "x11" 即新增 x11 变体并保留
        # surfaceless/drm 既有路径。x11 平台依赖 libx11/libxcb/xorgproto
        # 已在 requirements() 补齐（PkgConfigDeps 生成 x11.pc/xcb.pc，
        # meson dependency('x11')/dependency('xcb') 解析）。
        tc.project_options["platforms"] = "x11"
        # r24 全功能扩展：软件渲染器完整启用 softpipe + llvmpipe（LLVM 20.1.0
        # registry 二进制已验证可用）；r38 新增 x11 window 平台（EGL X11 变体
        # 与 GLX 所需的 X11 客户端依赖由 libx11/libxcb/xorgproto 提供，禁止
        # Xvfb 服务器端依赖混入）；Vulkan 仅 OHOS 可支持的 swrast(lavapipe)
        # 可尝试，需额外依赖，见 build 探测。
        tc.project_options["gallium-drivers"] = "softpipe,llvmpipe"
        tc.project_options["vulkan-drivers"] = ""
        tc.project_options["gbm"] = "enabled"
        tc.project_options["egl"] = "enabled"
        # r38（24.3.4.1.1.1）：glx=dri，产出 libGL.so.1/libGLX，供 GLX
        # 路径与 libepoxy 上游测试恢复（对照 24.3.4.1.1 glx=disabled）。
        # mesa 24.3.4 的 glx 选项只接受 auto/disabled/dri/xlib（不接受
        # enabled）；dri 配合既有 gbm/libdrm 软件路径，xlib 需另付 X 扩展
        # 链路，故按真实选项选 dri。
        tc.project_options["glx"] = "dri"
        tc.project_options["opengl"] = True
        tc.project_options["osmesa"] = True
        tc.project_options["gles1"] = "enabled"
        tc.project_options["gles2"] = "enabled"
        # r24：llvmpipe 需要 LLVM，启用（llvm/20.1.0 registry 二进制已验证）。
        # 实测 llvm-config 20.1.0 的 has-rtti 为 YES（LLVM_ENABLE_RTTI=ON），
        # meson.build 要求 mesa 保持 RTTI 一致（不得关闭 cpp_rtti）。
        tc.project_options["llvm"] = "enabled"
        tc.project_options["libunwind"] = "disabled"
        tc.project_options["valgrind"] = "disabled"
        tc.project_options["zstd"] = "disabled"
        # r38（24.3.4.1.1.1）R02：build-tests=true 全量实例化上游测试
        # （mesa 24.3.4 官方 tag 源码声明口径 3264 项，含 util/gallium/egl/gbm/
        # glx/compiler 各测试入口），消除基线 #11116 实测 2983/3264（91.4%）
        # 口径与 PR 正文 0/49 少报不一致（rule4 少报先例）；测试构建后由
        # 执行端在 Xvfb :199 环境全量实测并逐项记录。
        tc.project_options["build-tests"] = "true"
        tc.project_options["tools"] = ""
        tc.generate()
        # conan MesonToolchain 不把 tools.build:compiler_executables 的 ar/ranlib 写进
        # native file，meson 便按裸名 llvm-ar 探归档器；CI profile 只给 c/cpp，PATH 上
        # 无 llvm-ar 时 configure 失败（CI #36395: Unknown linker(s): [['llvm-ar']]）。
        # 从 c 编译器同目录推导 llvm-ar/llvm-ranlib 全路径注入 conan_meson_native.ini
        # （同 fontconfig/2.18.1 先例），不污染 PATH。
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        ar = ce.get("ar")
        rl = ce.get("ranlib")
        if not ar:
            cc = ce.get("c") or ""
            bindir = os.path.dirname(cc) if os.path.sep in cc else ""
            if bindir:
                cand = os.path.join(bindir, "llvm-ar")
                if os.path.isfile(cand):
                    ar = cand
                    rlc = os.path.join(bindir, "llvm-ranlib")
                    if os.path.isfile(rlc):
                        rl = rlc
        nf = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if ar and os.path.isfile(nf):
            with open(nf) as f:
                c = f.read()
            if "\nar =" not in c and "[binaries]" in c:
                ins = "[binaries]\nar = '%s'\n" % ar
                if rl:
                    ins += "ranlib = '%s'\n" % rl
                c = c.replace("[binaries]\n", ins, 1)
                with open(nf, "w") as f:
                    f.write(c)
        # r24：llvmpipe 的 LLVM config-tool 探测。meson dependency('llvm',
        # method:'config-tool') 优先读 native file [binaries] 的 llvm-config /
        # llvm-nm 声明，再回退 PATH。把 conan 依赖 llvm/20.1.0 包的工具全路径
        # 注入 native file，确保 20.1.0 的 LLVM 被选中并进入链接（而非系统
        # 15.0.4，后者导致 libLLVM 缺失）。
        if "llvm" in self.dependencies:
            llvm_pkg = self.dependencies["llvm"]
            llvm_bin = os.path.join(llvm_pkg.package_folder, "bin")
            if os.path.isdir(llvm_bin) and os.path.isfile(nf):
                with open(nf) as f:
                    c = f.read()
                adds = ""
                if "llvm-config =" not in c:
                    adds += "llvm-config = '%s'\n" % os.path.join(llvm_bin, "llvm-config")
                if "llvm-nm =" not in c:
                    adds += "llvm-nm = '%s'\n" % os.path.join(llvm_bin, "llvm-nm")
                if adds and "[binaries]" in c:
                    c = c.replace("[binaries]\n", "[binaries]\n" + adds, 1)
                    with open(nf, "w") as f:
                        f.write(c)

    def build(self):
        apply_conandata_patches(self)
        self._prepare_parser_tools()
        # r24：llvmpipe 需要 LLVM。meson 用 config-tool 探测 llvm-config，若 PATH
        # 上系统 llvm-config（15.0.4）优先，会链接错误版本的 LLVM 库甚至缺失。
        # 把 conan 依赖 llvm/20.1.0 包的 bin 前置到 PATH，确保 meson 探测到
        # 20.1.0 的 llvm-config 与链接库（ldc/spirv-llvm-translator 同款消费）。
        llvm_pkg = self.dependencies["llvm"]
        llvm_bin = os.path.join(llvm_pkg.package_folder, "bin")
        if os.path.isdir(llvm_bin):
            os.environ["PATH"] = llvm_bin + os.pathsep + os.environ.get("PATH", "")
        # Mesa 的 Meson 构建强制需要 Python mako >= 0.8.0（meson.build:917）。
        # 干净 CI 环境（/data/service/hnp/bin/python3）缺少 mako，导致 configure
        # 失败；在本机用户 site-packages 里偶然存在不代表 CI 可复现。参照仓库
        # acme-tiny-pyc 先例（build() 内 pip install），在 Meson configure 前
        # 确定性确保 mako 可用：先探测 import，缺失则 pip 安装，失败给出明确错误。
        try:
            import importlib.metadata as _im
            _mako_ver = _im.version("mako")
        except Exception:
            _mako_ver = ""
        if not _mako_ver:
            self.output.info("installing python mako (mesa meson build dependency)")
            rc = self.run("python3 -m pip install 'mako>=0.8.0' --quiet", env="conanbuild")
            if rc != 0:
                raise ConanException(
                    "mesa 构建需要 Python mako>=0.8.0，但直 pip 安装失败；"
                    "请确保构建环境可访问安装源或在 CI 环境预装 mako")
        meson = Meson(self)
        meson.configure()
        # OSMesa is needed by the headless desktop-OpenGL consumer; with
        # -Dgbm=enabled the gbm library target is also required so the package
        # ships gbm.pc/gbm.h/libgbm.so (r19 GBM 修复增量), and with
        # -Degl/enabled + gles1/gles2=enabled the EGL/GLES targets are built
        # for the EGL/GLES public header/lib/pkg-config artifact set (r22).
        # Building the explicit targets keeps the intermediate tree smaller
        # than the full default target set on the constrained OHOS device.
        # (OHOS 适配版 conan 2.29.1 的 Meson.build() 只接受单个 target 字符串；
        # 空格分隔多个目标是 meson compile 的原生多目标语法，行为等价于
        # `meson compile -C <build> OSMesa gbm libEGL ...`。)
        # EGL 目标（r27：恢复为 Shared Library 交付）。OHOS 系统 /lib64 自带
        # libEGL.so（系统图形栈），但 GTK4/GLib 通过 dlopen("libEGL.so.1") 动态
        # 加载 EGL——静态 libEGL.a 无法满足动态加载。r22 patch 0009 已撤销：
        # upstream shared_library 恢复，交付 libEGL.so.1.0.0（SONAME libEGL.so.1）
        # 及普通文件别名 libEGL.so.1/libEGL.so（package() 复制）。同名系统库
        # 冲突是符号/加载顺序语义而非文件系统污染（conan 隔离前缀），按任务
        # 授权交付共享 EGL 并以 dlopen 消费者实证明确加载。
        # r38（24.3.4.1.1.1）：目标列表加入 glx 库目标（mesa src/glx 的
        # shared_library('GL') 目标名 GL，产出 libGL.so.1 供 GLX 路径与
        # libepoxy 上游测试恢复）与 dril_dri（src/gallium/targets/dril，
        # 启用 x11/dri 后 meson install 要求 libdril_dri.so，缺失则
        # package() 中断——R01 构建实证）。
        # R02（build-tests=true 全量实例化）：meson install 额外要求
        # src/gallium/targets/pipe-loader 的 pipe_swrast.so（softpipe/swrast
        # 的 gallium-pipe 动态驱动，shared_library('pipe_swrast')），缺失则
        # package() 中断——R02 构建实证，一并加入目标列表。
        # EGL/GLES/OSMesa/GBM/llvmpipe 目标保持既有交付范围不变。
        meson.build(
            target="OSMesa gbm dri_gbm EGL GLESv1_CM GLESv2 GL dril_dri llvmpipe pipe_swrast"
        )

    def _prepare_parser_tools(self):
        """Rebind parser generators to packages in this isolated Conan graph."""
        bison = self.dependencies.build["bison"]
        bison_datadir = os.path.join(bison.package_folder, "share", "bison")
        if os.path.isdir(bison_datadir):
            os.environ["BISON_PKGDATADIR"] = bison_datadir
            os.environ["M4PATH"] = os.path.join(bison_datadir, "m4sugar")

        m4 = self.dependencies.build["m4"]
        m4_bin = os.path.join(m4.package_folder, "bin", "m4")
        if os.path.isfile(m4_bin):
            os.environ["M4"] = m4_bin
            os.environ["PATH"] = (
                os.path.dirname(m4_bin)
                + os.pathsep
                + os.environ.get("PATH", "")
            )
        else:
            raise ConanException(
                f"m4 executable is missing from the resolved package: {m4_bin}"
            )

    def package(self):
        import glob
        meson = Meson(self)
        # Do not let installation rebuild every unselected default target.
        meson.install(cli_args=["--no-rebuild"])
        # R03：llama visible=False 时其 runner 元数据不向下游传播；libgallium/
        # libOSMesa NEEDED libLLVM.so.20.1（运行时动态加载）。package() 阶段
        # llama 仍在 self.dependencies 中（构建依赖），把 llama lib 路径写入
        # package_folder 供 package_info()（test_package 上下文中 generators_
        # folder 为 None——第 30 次实证）读取并补进 runenv_info。
        try:
            _llvm = self.dependencies.get("llvm")
            if _llvm and _llvm.package_folder:
                _llvm_lib = os.path.join(_llvm.package_folder, "lib")
                if os.path.isdir(_llvm_lib):
                    with open(os.path.join(self.package_folder, "mesa_llvm_lib_dir"), "w") as _f:
                        _f.write(_llvm_lib)
        except Exception:
            pass
        # OHOS does not create the SONAME symlinks emitted by Meson. Publish
        # linker names as regular files so Conan consumers can resolve -lOSMesa,
        # -lglapi, -lgbm, -lEGL, -lGLESv2 and -lGLESv1_CM without depending on
        # filesystem symlink support.
        libdir = os.path.join(self.package_folder, "lib")
        for library, versioned in (
            ("libOSMesa.so", "libOSMesa.so.8.0.0"),
            ("libOSMesa.so.8", "libOSMesa.so.8.0.0"),
            ("libglapi.so", "libglapi.so.0.0.0"),
            ("libglapi.so.0", "libglapi.so.0.0.0"),
            ("libgbm.so", "libgbm.so.1.0.0"),
            ("libgbm.so.1", "libgbm.so.1.0.0"),
            ("libEGL.so", "libEGL.so.1.5.1"),
            ("libEGL.so.1", "libEGL.so.1.5.1"),
            ("libGL.so", "libGL.so.1.2.0"),
            ("libGL.so.1", "libGL.so.1.2.0"),
            ("libGLESv2.so", "libGLESv2.so.2.0.0"),
            ("libGLESv2.so.2", "libGLESv2.so.2.0.0"),
            ("libGLESv1_CM.so", "libGLESv1_CM.so.1.1.0"),
            ("libGLESv1_CM.so.1", "libGLESv1_CM.so.1.1.0"),
        ):
            source = os.path.join(libdir, versioned)
            linker_name = os.path.join(libdir, library)
            if os.path.isfile(source) and not os.path.exists(linker_name):
                shutil.copy2(source, linker_name)
        # Fall back to globbing whatever versioned file Meson actually emitted
        # for the EGL/GLES libs (exact patch version may differ by build).
        for base in ("libEGL.so", "libGLESv2.so", "libGLESv1_CM.so"):
            linker_name = os.path.join(libdir, base)
            if os.path.exists(linker_name):
                continue
            for cand in sorted(glob.glob(os.path.join(libdir, base + ".*"))):
                if os.path.isfile(cand):
                    shutil.copy2(cand, linker_name)
                    break
        self._sign_shared_libs()

    def _sign_shared_libs(self):
        """Re-sign installed ELF shared objects for the OHOS loader."""
        if str(self.settings.os) != "OHOS":
            return
        import glob

        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        libdir = os.path.join(self.package_folder, "lib")
        shared_objects = []
        for pattern in ("*.so", "*.so.*"):
            shared_objects.extend(glob.glob(os.path.join(libdir, pattern)))
        for shared_object in sorted(set(shared_objects)):
            if os.path.islink(shared_object):
                continue
            # Meson/lld output may contain a stale signature. Remove it before
            # binary-sign-tool appends the current OHOS self-signature.
            self.run(
                f'{objcopy} --remove-section .codesign "{shared_object}"',
                ignore_errors=True,
            )
            self.run(
                f'{signer} sign -inFile "{shared_object}" '
                f'-outFile "{shared_object}" -selfSign 1'
            )

    def package_info(self):
        # R03：补全导出 libs（下游 Conan 消费者走 CMakeDeps 时可规范链接
        # libGL.so.1/libEGL.so.1/libgbm.so/libGLESv2.so，无需手动 -L 绕过；
        # mplayer 侧反馈——此前仅导出 OSMesa，CMakeDeps 只链 OSMesa）。
        # R01 产物实际存在：libGL.so.1（SONAME libGL.so.1）、libEGL.so.1、
        # libgbm.so.1、libGLESv2.so.2、libGLESv1_CM.so.1、libOSMesa.so.8。
        # 说明：llvm 依赖 cmake_find_mode=none（无 CMakeDeps config），拆
        # components 时 Conan 2 校验强制所有直接 requires 被引用，而引用
        # llvm::llvm 会使下游 find_dependency(LLVM) 失败（多次实证）；故采用
        # 顶层 libs 补全形态（同 ldc/libomptarget 先例），mesa::mesa 携带
        # 全部链接库（-lGL/-lEGL/-lgbm 自动解析），不拆独立 components target。
        self.cpp_info.libs = [
            "GL",
            "EGL",
            "gbm",
            "GLESv2",
            "GLESv1_CM",
            "OSMesa",
        ]
        # R03：requires 置空——llama visible=False（脱离 CMakeDeps），运行时
        # libLLVM 由下方 runenv_info 文件传递补充；libx11/xcb 等 X11 客户端
        # 链保持可见（其 libdirs 自动聚合，GL/EGL 消费者运行时可用）。
        self.cpp_info.requires = []
        # Mesa desktop OpenGL, EGL, GBM, GLES and OSMesa headers.
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.runenv_info.append_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib")
        )
        # R03：llama visible=False，其 runenv 不自动传播；libgallium/libOSMesa
        # NEEDED libLLVM.so.20.1（运行时动态加载）。读取 generate() 写入
        # generators_folder 的 llama lib 路径（文件传递，规避实例属性跨方法
        # 不可靠——第 22/24 次实证），补进 mesa runenv_info 供 test_package/
        # 消费者运行时解析。package() 阶段会把该文件再写入 package_folder，
        # 保证 test_package 上下文中也能读到（generators_folder 在该上下文
        # 为 None——第 30 次实证）。
        _llvm_lib = None
        for _base in (self.generators_folder, self.package_folder):
            if _base:
                try:
                    with open(os.path.join(_base, "mesa_llvm_lib_dir")) as _f:
                        _llvm_lib = _f.read().strip()
                    if _llvm_lib and os.path.isdir(_llvm_lib):
                        break
                except Exception:
                    continue
        if _llvm_lib and os.path.isdir(_llvm_lib):
            self.runenv_info.append_path("LD_LIBRARY_PATH", _llvm_lib)
        # R03：llvm 保持可见 requires，其运行时 libLLVM.so.20.1 的解析由
        # 消费者/test_package 的 conanrun 环境提供（llvm 可见依赖 runenv
        # 自动聚合）；不再在 package_info() 访问 llvm package_folder
        # （conan create 的 package_info 阶段该属性为 None，第 5/13/14 次
        # 实证）。test() 端由 test_package/conanfile.py 显式补 llvm lib 路径
        self.cpp_info.set_property("cmake_file_name", "mesa")
        self.cpp_info.set_property("cmake_target_name", "mesa::mesa")
