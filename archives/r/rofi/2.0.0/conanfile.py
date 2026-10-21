#!/usr/bin/env python3
r"""Conan recipe — rofi 2.0.0（窗口切换器/应用启动器，Meson 构建，Wayland 后端）

rofi：快速可定制的窗口切换器/应用启动器（C；Cairo/Pango 自绘渲染，不依赖 GTK）。
2.0.0 采用 Meson 构建，Wayland/X11 双后端，捆绑子工程 libnkutils / libgwater-wayland /
libgwater-xcb。

OHOS PC 适配（Wayland 路线；X11 路线因 5 个 xcb 依赖未发布到制品仓而阻塞）：
- meson 选项: -Ddefault_library=shared（子工程 libnkutils library() 随动）
  -Dxcb=disabled -Dwayland=enabled -Dimdkit=false（xcb-imdkit 未发布）
  -Dcheck=enabled（运行 3 个 check 门控的上游测试）
- 宿主工具 .codesign 修复（appstream/1.2.0 先例 R06）：wayland-scanner（wayland 包）、
  glib-compile-resources（glib 包）在 .conan2 包内直接执行报 EPERM/code=126 →
  复制到构建私有目录 + llvm-objcopy --remove-section .codesign +
  binary-sign-tool sign -selfSign 1，wrapper（export LD_LIBRARY_PATH）exec 已签名副本，
  注册进机器文件 [binaries]（meson find_program 优先读机器文件）
- .pc 补全（PkgConfigDeps 只为依赖 package_info 声明的组件生成 .pc）：
  gio-2.0（追加 meson gnome 模块需要的 glib_compile_resources 变量，指向已签名
  wrapper）、gio-unix-2.0、gmodule-no-export-2.0、pangocairo、pangoft2、
  wayland-cursor、wayland-protocols（pkgdatadir 变量）
- check 0.15.2：OHOS /tmp 只读，其 P_tmpdir 编译期固定 "/tmp" 且优先级高于
  TMPDIR → 测试临时文件失败 exit(2) → build() 注入 TEMP 指向构建私有目录；
  测试二进制的宿主库路径经 LD_LIBRARY_PATH 注入（aravis/0.8.36 先例）
- libnkutils（捆绑子工程）format-string 越界写修复（patches/；上游
  sardemff7/libnkutils master 与捆绑版一致、缺陷未修复）：_nk_format_string_parse
  的 '/' 分支中 count 循环原位删除转义序列（反斜杠+字符 → 字符）使字符串尾部左移，
  但外层 e（} 位置）未随之更新 → 其后配对扫描 do{...}while(w<e) 多走一轮 →
  token.replace[c].regex = NULL 写到 g_new(c) 数组末尾之后 8 字节（堆越界写）。
  Linux 分配器 size-class 舍入（48→64）使越界落 slack 内无害（上游 CI 绿）；
  OHOS 分配器无此舍入 → 堆元数据损坏 → replace 阶段 GString 几何增长撞
  G_MAXSIZE/2 分配上限崩溃（format-string/replace/escaping/forwardslash/3，
  exit 133/139）。建议向上游报告。

上游: https://github.com/DaviDar/rofi
"""
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import PkgConfigDeps
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.layout import basic_layout


class RofiConan(ConanFile):
    name = "rofi"
    version = "2.0.0"
    description = "rofi — fast and customizable window switcher / application launcher (Wayland backend)"
    license = "MIT"
    homepage = "https://github.com/DaviDar/rofi"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    # PkgConfigDeps/VirtualBuildEnv 在 generate() 内手动调用（类级 generators 先于
    # generate() 运行，会破坏 .pc 补全与组件注入的顺序）
    generators = []

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 核心依赖（meson.build @ 2.0.0 的 dependency() 调用）
        self.requires("glib/2.84.0.1")
        self.requires("cairo/1.18.4")
        self.requires("pango/1.56.4")
        self.requires("gdk-pixbuf/2.44.6.1.1")
        self.requires("libxkbcommon/1.13.1")
        # Wayland 后端（xcb 路线阻塞：xcb/xcb-aux/xcb-xkb/xcb-ewmh/xcb-icccm 等未发布）
        self.requires("wayland/1.22.0")
        self.requires("wayland-protocols/1.36")
        # 传递 .pc 提升为直接依赖（hyprpicker/0.4.7 先例：纯传递依赖在干净图下
        # 为 "Skipped binaries"，其 .pc 缺失）
        self.requires("libffi/3.4.4")
        self.requires("zlib/1.3.1.1")
        self.requires("pcre2/10.45")
        self.requires("graphite2/1.3.14")
        # 版本冲突（hyprpicker 先例，API 兼容）
        self.requires("expat/2.8.2", override=True)
        self.requires("fontconfig/2.18.1", override=True)

    def build_requirements(self):
        # 主题/关键字解析器生成工具（meson find_program 经 conanbuild PATH 命中）
        self.tool_requires("flex/2.6.4.2")
        self.tool_requires("bison/3.8.2")
        # 上游测试框架（3 个 check 门控测试）
        self.test_requires("check/0.15.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # OHOS worker 导出 AR/AS/STRIP/NM/RANLIB 裸名且 posix_spawn 不搜索 PATH
        # （appstream 先例）：先剔除坏值，再按绝对路径固定
        for _var in ("AR", "AS", "STRIP", "NM", "RANLIB"):
            os.environ.pop(_var, None)
        _tools = {n: shutil.which(n) for n in ("ar", "as", "nm", "ranlib")}
        _missing = [n for n, p in _tools.items() if p is None]
        if _missing:
            raise ConanInvalidConfiguration(
                f"Required build tools not found in PATH: {', '.join(_missing)}")
        tc = MesonToolchain(self)
        tc.ar = _tools["ar"]
        tc.as_ = _tools["as"]
        tc.strip = None
        tc.binaries["nm"] = _tools["nm"]
        tc.binaries["ranlib"] = _tools["ranlib"]

        # meson 选项（与探索构建一致，143/143 目标）
        tc.project_options["default_library"] = "shared"
        tc.project_options["xcb"] = "disabled"
        tc.project_options["wayland"] = "enabled"
        tc.project_options["imdkit"] = "false"
        tc.project_options["check"] = "enabled"
        tc.project_options["drun"] = "true"
        tc.project_options["window"] = "true"

        PkgConfigDeps(self).generate()
        gen = self.generators_folder

        def _pkg_folder(dep_name, pc_name):
            folder = None
            try:
                folder = self.dependencies[dep_name].package_folder
            except KeyError:
                pass
            if not folder:
                # 干净解析下 package_folder 可能为 None：以已生成 .pc 的 prefix 兜底
                pc = os.path.join(gen, pc_name)
                if os.path.isfile(pc):
                    with open(pc, encoding="utf-8") as fh:
                        for line in fh:
                            if line.startswith("prefix="):
                                folder = line.strip().split("=", 1)[1]
                                break
            return folder

        glib_pkg = _pkg_folder("glib", "glib-2.0.pc")
        pango_pkg = _pkg_folder("pango", "pango.pc")
        wayland_pkg = _pkg_folder("wayland", "wayland-client.pc")
        wpro_pkg = _pkg_folder("wayland-protocols", "wayland-protocols.pc")
        for folder, dep in ((glib_pkg, "glib"), (pango_pkg, "pango"),
                            (wayland_pkg, "wayland"), (wpro_pkg, "wayland-protocols")):
            if not folder:
                raise ConanInvalidConfiguration(f"cannot resolve package folder of {dep}")

        # --- 宿主工具 .codesign 修复（appstream/1.2.0 先例 R06）---
        tools_dir = os.path.join(self.build_folder, "rofi-tools")
        os.makedirs(tools_dir, exist_ok=True)
        _objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        _signtool = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        for exe in (_objcopy, _signtool):
            if not os.path.isfile(exe):
                raise ConanInvalidConfiguration(f"signing tool missing: {exe}")
        wrappers = {}
        for tool, src_pkg in (("wayland-scanner", wayland_pkg),
                              ("glib-compile-resources", glib_pkg)):
            src = os.path.join(src_pkg, "bin", tool)
            if not os.path.isfile(src):
                raise ConanInvalidConfiguration(f"build tool missing: {src}")
            dst = os.path.join(tools_dir, tool + ".bin")
            shutil.copy2(src, dst)
            with open(dst, "rb") as fh:
                is_elf = fh.read(4) == b"\x7fELF"
            if is_elf:
                subprocess.run(
                    [_objcopy, "--remove-section", ".codesign", dst],
                    check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                r = subprocess.run(
                    [_signtool, "sign", "-inFile", dst, "-outFile", dst,
                     "-selfSign", "1"],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                if r.returncode != 0:
                    raise ConanInvalidConfiguration(
                        f"binary-sign-tool self-sign failed for {tool}: {r.stdout.strip()}")
            os.chmod(dst, 0o755)
            wrapper = os.path.join(tools_dir, tool)
            with open(wrapper, "w", encoding="utf-8") as fh:
                fh.write("#!/bin/sh\n")
                fh.write(f"export LD_LIBRARY_PATH={src_pkg}/lib:$LD_LIBRARY_PATH\n")
                fh.write(f'exec "{dst}" "$@"\n')
            os.chmod(wrapper, 0o755)
            wrappers[tool] = wrapper
        tc.binaries["wayland-scanner"] = wrappers["wayland-scanner"]
        tc.binaries["glib-compile-resources"] = wrappers["glib-compile-resources"]
        self.buildenv_info.prepend_path("PATH", tools_dir)

        # --- .pc 补全（写入 generators 目录，覆盖生成版 stub）---
        def _write_pc(name, content):
            with open(os.path.join(gen, name), "w", encoding="utf-8") as fh:
                fh.write(content)

        # gio-2.0.pc：保留生成版（prefix/libs 正确），追加 meson gnome 模块需要的
        # glib_compile_resources 变量（指向已签名 wrapper；meson 无论经 .pc 变量
        # 还是 find_program 解析工具，都落到可执行签名副本）
        gio_pc = os.path.join(gen, "gio-2.0.pc")
        if os.path.isfile(gio_pc):
            with open(gio_pc, encoding="utf-8") as fh:
                text = fh.read()
            if "glib_compile_resources" not in text:
                additions = []
                if "bindir=" not in text:
                    additions.append("bindir=${prefix}/bin")
                additions.append(
                    f"glib_compile_resources={wrappers['glib-compile-resources']}")
                text += "\n" + "\n".join(additions) + "\n"
                with open(gio_pc, "w", encoding="utf-8") as fh:
                    fh.write(text)

        _write_pc("gio-unix-2.0.pc",
            f"prefix={glib_pkg}\n"
            "includedir=${prefix}/include\n"
            "\n"
            "Name: GIO unix specific APIs\n"
            "Description: unix specific headers for glib I/O library\n"
            "Version: 2.84.0.1\n"
            "Requires: gobject-2.0, gio-2.0\n"
            "Cflags: -I${includedir}/gio-unix-2.0\n")
        _write_pc("gmodule-no-export-2.0.pc",
            f"prefix={glib_pkg}\n"
            "includedir=${prefix}/include\n"
            "libdir=${prefix}/lib\n"
            "\n"
            "gmodule_supported=true\n"
            "\n"
            "Name: GModule\n"
            "Description: Dynamic module loader for GLib\n"
            "Version: 2.84.0.1\n"
            "Requires: glib-2.0\n"
            "Libs: -L${libdir} -lgmodule-2.0 -pthread\n"
            "Cflags: -I${includedir} -pthread\n")
        _write_pc("pangocairo.pc",
            f"prefix={pango_pkg}\n"
            "includedir=${prefix}/include\n"
            "libdir=${prefix}/lib\n"
            "\n"
            "Name: Pango Cairo\n"
            "Description: Cairo rendering support for Pango\n"
            "Version: 1.56.4\n"
            "Requires: pango, cairo >= 1.18.0\n"
            "Libs: -L${libdir} -lpangocairo-1.0\n"
            "Cflags: -I${includedir}/pango-1.0\n")
        _write_pc("pangoft2.pc",
            f"prefix={pango_pkg}\n"
            "includedir=${prefix}/include\n"
            "libdir=${prefix}/lib\n"
            "\n"
            "Name: Pango FT2 and Pango Fc\n"
            "Description: FreeType 2.0 and fontconfig font support for Pango\n"
            "Version: 1.56.4\n"
            "Requires: pango, freetype2, fontconfig >= 2.15.0\n"
            "Libs: -L${libdir} -lpangoft2-1.0\n"
            "Cflags: -I${includedir}/pango-1.0\n")
        _write_pc("wayland-cursor.pc",
            f"prefix={wayland_pkg}\n"
            "includedir=${prefix}/include\n"
            "libdir=${prefix}/lib\n"
            "\n"
            "Name: Wayland Cursor\n"
            "Description: Wayland cursor helper library\n"
            "Version: 1.22.0\n"
            "Requires.private: wayland-client\n"
            "Libs: -L${libdir} -lwayland-cursor\n"
            "Cflags: -I${includedir}\n")
        _write_pc("wayland-protocols.pc",
            f"prefix={wpro_pkg}\n"
            "datarootdir=${prefix}/share\n"
            "pkgdatadir=${datarootdir}/wayland-protocols\n"
            "\n"
            "Name: Wayland Protocols\n"
            "Description: Wayland protocol files\n"
            "Version: 1.36\n")

        # flex/bison/check（tool_requires）bin 目录进 PATH（meson find_program）
        VirtualBuildEnv(self).generate()

        # 绝对路径 DT_NEEDED 兼容（ohpcd 预编译 fontconfig/2.18.1 烘焙构建机
        # CONAN_HOME 路径，CI 根为 ~/.cache/conan2 → 测试 exit 127，CI 第 1 轮根因）
        self._fix_absolute_needed()

        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        self._run_upstream_tests()

    def _fix_absolute_needed(self):
        """OHOS 兼容 shim（CI 第 1 轮失败根因修复，2026-10-16 #95940）。

        ohpcd 制品仓预编译包可能在构建时烘焙绝对路径 DT_NEEDED
        （fontconfig/2.18.1 → /…/.conan2/p/expat…/lib/libexpat.so，即构建
        worker 的 CONAN_HOME）；CI worker 的 CONAN_HOME 为 ~/.cache/conan2，
        烘焙路径不存在 → 动态 loader 失败 → 测试二进制 exit 127。本机
        CONAN_HOME 恰为 ~/.conan2（烘焙路径存在）→ 本地 W3 侥幸通过，CI 必挂。

        处理：扫描全部 host 依赖 .so 的 DT_NEEDED，对缺失的绝对路径在当前
        cache 建指向同 basename 真实库的符号链接。加性/幂等/非致命：仅在
        CONAN_HOME 根下新建符号链接（CI worker 构建后环境还原；本机路径
        已存在 → no-op）。正解为 ohpcd 重发 fontconfig 改按 soname 链接
        （见 notes.md "CI 第 1 轮失败分析"）。
        """
        _readelf = (shutil.which("readelf") or shutil.which("llvm-readelf")
                    or "/data/service/hnp/bin/readelf")
        if not os.path.isfile(_readelf):
            self.output.warning("[abs-needed-shim] readelf 不可用，跳过（非致命）")
            return
        dep_lib_dirs = []
        for dep in self.dependencies.host.values():
            pf = dep.package_folder
            if not pf:
                continue
            for d in dep.cpp_info.libdirs:
                p = d if os.path.isabs(d) else os.path.join(pf, d)
                if os.path.isdir(p) and p not in dep_lib_dirs:
                    dep_lib_dirs.append(p)
        # basename -> 当前 cache 内真实文件（符号链接目标）
        real_by_name = {}
        for d in dep_lib_dirs:
            for f in os.listdir(d):
                p = os.path.join(d, f)
                if (f.endswith(".so") or ".so." in f) \
                        and (os.path.isfile(p) or os.path.islink(p)):
                    real_by_name.setdefault(f, p)
        # 扫描绝对路径 NEEDED 条目（readelf: (NEEDED) Shared library: [/abs]）
        abs_needed = set()
        for d in dep_lib_dirs:
            for f in os.listdir(d):
                if not (f.endswith(".so") or ".so." in f):
                    continue
                p = os.path.join(d, f)
                try:
                    r = subprocess.run([_readelf, "-d", p],
                                       capture_output=True, text=True, timeout=60)
                    for line in r.stdout.splitlines():
                        if "NEEDED" not in line:
                            continue
                        m = (re.search(r"\[(/[^]]+)\]", line)
                             or re.search(r"NEEDED\)\s+(/\S+)", line))
                        if m:
                            abs_needed.add(m.group(1))
                except Exception:
                    pass
        created = []
        for n in sorted(abs_needed):
            if os.path.islink(n) or os.path.exists(n):
                continue  # 已存在（含 CONAN_HOME==烘焙根）→ no-op
            base = os.path.basename(n)
            real = real_by_name.get(base)
            if real is None:
                # 无版本名（libfoo.so）→ 取版本化最长匹配（dev 符号链接语义）
                cands = sorted((q for k, q in real_by_name.items()
                                if k.startswith(base + ".")),
                               key=lambda q: len(os.path.basename(q)),
                               reverse=True)
                real = cands[0] if cands else None
            if real is None:
                self.output.warning(f"[abs-needed-shim] basename {base} 无对应库 "
                                    f"(abs needed {n})，跳过")
                continue
            try:
                os.makedirs(os.path.dirname(n), exist_ok=True)
                os.symlink(real, n)
                created.append((n, real))
            except Exception as e:
                self.output.error(f"[abs-needed-shim] link {n} -> {real} 失败: {e}")
        if created:
            self.output.info(f"[abs-needed-shim] 为 {len(created)} 个绝对路径 "
                             f"DT_NEEDED 创建兼容符号链接:")
            for n, real in created:
                self.output.info(f"[abs-needed-shim]   {n} -> {real}")

    def _run_upstream_tests(self):
        # check 0.15.2：P_tmpdir 编译期固定 "/tmp"（OHOS 只读），优先级高于
        # TMPDIR → 临时文件创建失败 exit(2)；TEMP 为其第一优先级 → 指向构建私有目录
        tempdir = os.path.join(self.build_folder, "test-tmp")
        os.makedirs(tempdir, exist_ok=True)
        # 测试二进制需宿主依赖库（meson build rpath 只覆盖树内库如 libnkutils）→
        # 注入 LD_LIBRARY_PATH（aravis/0.8.36 先例）
        libdirs = []
        for ctx in ("host", "build"):
            for dep in getattr(self.dependencies, ctx).values():
                pf = dep.package_folder
                if not pf:
                    continue
                for d in dep.cpp_info.libdirs:
                    p = d if os.path.isabs(d) else os.path.join(pf, d)
                    if os.path.isdir(p) and p not in libdirs:
                        libdirs.append(p)
        old_temp = os.environ.get("TEMP")
        old_ld = os.environ.get("LD_LIBRARY_PATH")
        os.environ["TEMP"] = tempdir
        os.environ["LD_LIBRARY_PATH"] = ":".join(libdirs)
        try:
            Meson(self).test()
        finally:
            if old_temp is None:
                os.environ.pop("TEMP", None)
            else:
                os.environ["TEMP"] = old_temp
            if old_ld is None:
                os.environ.pop("LD_LIBRARY_PATH", None)
            else:
                os.environ["LD_LIBRARY_PATH"] = old_ld

    def _sign_elf(self, path):
        """移除 .codesign 段后自签（appstream R06 / aravis _sign_shared_libs 同流程）"""
        _objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        _signtool = (shutil.which("binary-sign-tool")
                     or "/data/service/hnp/bin/binary-sign-tool")
        subprocess.run(
            [_objcopy, "--remove-section", ".codesign", path],
            check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        r = subprocess.run(
            [_signtool, "sign", "-inFile", path, "-outFile", path, "-selfSign", "1"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        if r.returncode != 0:
            raise ConanInvalidConfiguration(
                f"binary-sign-tool self-sign failed for {path}: {r.stdout.strip()}")
        os.chmod(path, 0o755)

    def package(self):
        Meson(self).install()
        # OHOS 包树（.conan2/p/.../p/）内的可执行二进制受 .codesign 校验约束：
        # 构建期自产签名在包树原位 exec 报 EPERM/code=126（实测：builddir/复制到
        # $HOME 均可执行，唯包树原位被拒）→ 打包后对 bin/rofi 重新自签
        rofi_bin = os.path.join(self.package_folder, "bin", "rofi")
        if os.path.isfile(rofi_bin):
            self._sign_elf(rofi_bin)
        # ohpcd wayland/1.22.0 包内 libwayland-cursor.so.0.22.0 的 .codesign 失效：
        # dlopen 报 EACCES(errno=13)（实测对照：同包 libwayland-client 正常加载；
        # 自签副本通过签名校验；上游 meson test 未暴露因 12 个 check 测试二进制均
        # 不 NEEDED cursor，唯 rofi 主二进制链接）→ 复制重签到包内 lib/ 并经
        # runenv_info 前置 LD_LIBRARY_PATH（aravis 先例）
        wl_pkg = self.dependencies["wayland"].package_folder
        if wl_pkg:
            repack = os.path.join(self.package_folder, "lib")
            os.makedirs(repack, exist_ok=True)
            for so in os.listdir(os.path.join(wl_pkg, "lib")):
                if so.startswith("libwayland-cursor"):
                    src = os.path.join(wl_pkg, "lib", so)
                    if os.path.isfile(src) and not os.path.islink(src):
                        dst = os.path.join(
                            repack, "libwayland-cursor.so.0"
                            if so != "libwayland-cursor.so.0" else so)
                        shutil.copy2(src, dst)
                        self._sign_elf(dst)

    def package_info(self):
        # rofi 为纯 CLI 应用：bin/rofi + share/ 数据（themes/desktop/icons）；
        # 无对外可链接库。lib/ 内为重签后的 wayland-cursor 运行时副本
        # （ohpcd wayland/1.22.0 包内原件 .codesign 失效，dlopen EACCES）。
        # libdirs 声明 lib/ 后，消费者 conanrun 环境（VirtualRunEnv）自动将
        # 该目录汇入 LD_LIBRARY_PATH，且直接依赖目录先于传递依赖（wayland）
        # 目录，重签副本优先被加载
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = []
