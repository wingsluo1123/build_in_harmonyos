#!/usr/bin/env python3
"""Conan recipe — lite (lite-xl) 2.1.8 (meson, application).

Lite XL is a lightweight text editor written in C with an embedded Lua
runtime, built with Meson.  This recipe produces the `lite-xl` executable
(bin/) plus its runtime data (share/lite-xl).

Dependency policy (R27/R36): every dependency comes from the conan registry
via pkg-config (PkgConfigDeps); meson subprojects are disabled
(wrap_mode=nodownload) so a missing dependency fails loudly instead of being
silently replaced by a network download.
"""
from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class LiteConan(ConanFile):
    name = "lite"
    version = "2.1.8"
    description = "Lite XL — a lightweight, fast and free text editor written in Lua and C (lite-xl 2.1.8)"
    license = "MIT"
    homepage = "https://lite-xl.com/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # lite-xl 2.1.8 的 meson 依赖（均经 pkg-config 查找，PkgConfigDeps 生成 .pc）。
        # 【环境阻塞待验证】各依赖具体版本/上游 meson 依赖名须在真实环境核实。
        # SDL3 切换依据：本仓有 sdl3/3.4.8 OHOS 适配归档（archives/s/sdl3/3.4.8/，
        #   status built、platform ohos-aarch64、G0-G4 pass、4 个 OHOS 补丁），但
        #   **无 conan 配方**（无 conanfile.py/conandata.yml）→ 无法被 conan requires。
        #   故本配方暂用 SDL2；SDK3 切换路径（R36）：把 sdl3/3.4.8 归档补全为 conan
        #   配方并发布后，将下面换成 self.requires("sdl3/3.4.8") 并按上游 prefer_sdl3
        #   逻辑构建，复用归档 4 补丁知识（SDL_PLATFORM_OHOS + 取消 SDL_PLATFORM_LINUX、
        #   禁用 pthread_setcanceltype、禁用 SDL_TRAY / SDL_Gtk_Quit）。详见 notes.md。
        self.requires("sdl2/2.30.10")      # 上游优先 SDL3；sdl3 归档无配方 → 暂用 SDL2
        self.requires("freetype/2.14.3")   # pkg-config 名 freetype2（本仓配方已正确设置）
        self.requires("lua/5.4.8")         # pkg-config 名 lua-5.4（generate() 里补 lua.pc 别名，见下）
        self.requires("pcre2/10.45.1")     # pkg-config 名 libpcre2-8（本仓配方组件化输出）
        # agg：lite-xl 以 meson subproject（git wrap）引入，无 pkg-config，本仓**无 agg
        #   配方**（已核实 archives/a/agg 目录不存在，且无任何 agg 归档）。
        #   —— W0/R36 阻塞：如需完全离线构建，必须先适配并发布 agg 包（并让 lite-xl 的
        #      meson.build 改为 dependency('agg')，见 notes.md），然后取消下面这行注释：
        # self.requires("agg/2.6")   # 【环境阻塞待验证】

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def layout(self):
        basic_layout(self, src_folder=".")

    def generate(self):
        PkgConfigDeps(self).generate()
        tc = MesonToolchain(self)
        # 依赖全走 conan（R36）：禁止 meson 偷偷下载 wrap 子项目，缺了当场报错。
        tc.project_options["wrap_mode"] = "nodownload"
        # dav1d 教训（musl）：严格 c99 不自动定义 _POSIX_C_SOURCE，POSIX 函数检测误判失败。
        # lite-xl 上游默认 gnu11，这里显式钉死，避免检测函数在 musl 上失败。
        tc.project_options["c_std"] = "gnu11"
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        tc.generate()
        self._inject_meson_archiver()
        self._ensure_lua_pkgconfig_alias()

    def _inject_meson_archiver(self):
        # 【OHOS 必需】conan 的 MesonToolchain 不把 tools.build:compiler_executables 里的
        # ar/ranlib 写进 native file，meson 便按裸名 llvm-ar 探归档器；而 clang 工具链在
        # /data/service/hnp/bin，PATH 上没有 llvm-ar 时 meson configure 直接失败。
        # 把 ar/ranlib 全路径注入 conan_meson_native.ini，不污染 PATH。（dav1d/fontconfig 实证）
        import os
        _ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        _ar, _rl = _ce.get("ar"), _ce.get("ranlib")
        if not _ar:
            _cc = _ce.get("c") or ""
            _bindir = os.path.dirname(_cc) if os.path.sep in _cc else ""
            if _bindir:
                _cand = os.path.join(_bindir, "llvm-ar")
                if os.path.isfile(_cand):
                    _ar = _cand
                    _rlc = os.path.join(_bindir, "llvm-ranlib")
                    if os.path.isfile(_rlc):
                        _rl = _rlc
        _nf = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if not (_ar and os.path.isfile(_nf)):
            return
        with open(_nf, encoding="utf-8") as _f:
            _c = _f.read()
        if "\nar =" in _c or "[binaries]" not in _c:
            return
        _ins = "[binaries]\nar = '%s'\n" % _ar
        if _rl:
            _ins += "ranlib = '%s'\n" % _rl
        with open(_nf, "w", encoding="utf-8") as _f:
            _f.write(_c.replace("[binaries]\n", _ins, 1))

    def _ensure_lua_pkgconfig_alias(self):
        # lite-xl 的 meson.build 用 dependency('lua') 找 Lua，而本仓 lua/5.4.8 配方的
        # pkg-config 名是 lua-5.4（无 lua.pc → meson 报 "Dependency 'lua' not found"）。
        # 这里在 generators 目录补 lua.pc / lua5.4.pc 别名，转发到 conan 生成的 lua-5.4.pc。
        # 【环境阻塞待验证】上游 meson 具体依赖名须在真实环境核实；若实际请求 lua5.4 / lua-5.4，
        # 对应别名已覆盖；若都未命中则按实况调整（本辅助函数多余时无害）。
        import os
        _gf = self.generators_folder
        _version = "5.4.8"
        try:
            _version = str(self.dependencies["lua"].ref.version)
        except (KeyError, AttributeError):
            pass
        for _alias in ("lua", "lua5.4"):
            _p = os.path.join(_gf, _alias + ".pc")
            if os.path.isfile(_p):
                continue
            try:
                with open(_p, "w", encoding="utf-8") as _f:
                    _f.write(
                        "Name: %s\n"
                        "Description: pkg-config alias for conan lua "
                        "(lite-xl meson requests dependency('%s'))\n"
                        "Version: %s\n"
                        "Requires: lua-5.4\n" % (_alias, _alias, _version)
                    )
            except (IOError, OSError):
                self.output.warning("failed to write %s.pc alias (non-fatal)" % _alias)

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        Meson(self).install()
        # R32: settings.os 判断必须用 in ("Linux", "OHOS")，不能 == "Linux"。
        # 签名工具仅在 OHOS 设备存在，_sign_binaries 内部按工具是否存在跳过
        # （Linux 主机上执行无副作用）。
        if self.settings.os in ("Linux", "OHOS"):
            self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # 鸿蒙 PC XPM 要求被 exec 的可执行文件（及 dlopen 的 .so）带代码签名，否则报
        # Permission denied / Operation not permitted（dav1d/1.5.0、fontconfig 实证）。
        # ① lib/ 的 .so  ② bin/ 的 ELF 可执行文件（lite-xl 本体）。
        import glob
        import os
        targets = glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so"), recursive=True)
        targets += glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so.*"), recursive=True)
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for name in os.listdir(bindir):
                p = os.path.join(bindir, name)
                if os.path.isfile(p) and not os.path.islink(p) and self._is_elf(p):
                    targets.append(p)
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not (os.path.isfile(signer) and os.path.isfile(objcopy)):
            self.output.info("sign tool not found — skip signing (non-OHOS host?)")
            return
        for f in targets:
            if os.path.islink(f):  # 只签真实 ELF，跳版本化 .so 的软链（否则对同一目标重复签）
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def package_info(self):
        # application package：可执行文件在 bin/，运行时数据在 share/lite-xl（非库，无 cpp_info.libs）。
        self.cpp_info.bindirs = ["bin"]
        # R32: Linux-like 平台（Linux / OHOS）统一处理。lite-xl 运行期依赖 libm/libdl/libpthread
        # （内嵌 Lua + dlopen），供可能的消费者参考。
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["dl", "m", "pthread"]
