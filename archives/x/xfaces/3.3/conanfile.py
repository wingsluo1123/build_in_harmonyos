"""Conan recipe — xfaces 3.3 (X11 faces/mail 监视器, Christopher B. Liebman 1994).

构建单元提取（imake 规避）:
- 上游仅提供 imake 生成的 Makefile（绑定 sun.cf/X11R5）与 Makefile.noimake
  （绑定 /usr/X11R5 前缀 + netaudio libaudio，Makefile.noimake 的链接规则
  还引用了错误的目标变量 $(TARGET)/$(LIBS)/$(IDIRS)——实际定义是
  $(xfaces)/$(LIBS) 不一致，直接 make 失败）。两者在 OHOS 上均不可用，
  配方按 Makefile.noimake 的编译单元自写编译命令（myman/4.0.116 同款模式）。
- 编译单元 = 源码根目录全部 33 个 .c 减去 face_sound.c（netaudio 音频后端，
  OHOS 无 libaudio，可选特性裁剪；XPM/SHAPE/XFACE/POP/LOOKUP_HOSTNAME
  均保留，可选依赖在制品仓全部已发布）。
- 宏定义对齐 Makefile.noimake 启用集：-DXPM -DSHAPE -DXFACE -DPOP
  -DLOOKUP_HOSTNAME（sound 关闭）。

依赖（全部制品仓已发布二进制，W0 conan download 实测）:
- libxaw/1.0.14（传递拉入 libxt/libxmu/libxpm/xorgproto）
- libxext/6.4.0.1（X11/extensions/shape.h，SHAPE 支持）
- libx11/6.4.0 + libxcb/1.16 + libxau/1.0.11（运行期，myman 同款 run=True）
- compface/1.5.2（X-Face 图像解码，XFACE 支持）
- xorgproto/2025.1（协议头）

测试:
- 上游无测试套件（无 test/check 目标，tarball 内无测试目录，grep 实证）。
- test_package 真实执行被测二进制（R34）：xfaces 为 X11 GUI 应用，无 -h/-v
  参数；以无效 DISPLAY 运行，XtInitialize 打印 "Error: Can't open display:"
  后退出——证明二进制可执行且 X11/Xaw/Xmu/Xt/Xpm/compface 动态链接成功。
"""

import os
import shlex
import shutil

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class XfacesConan(ConanFile):
    name = "xfaces"
    version = "3.3"
    description = "X11 application displaying mail/faces from the mail spool"
    license = "MIT"
    homepage = "https://snapshot.debian.org/package/xfaces/"
    url = "https://snapshot.debian.org/package/xfaces/"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        # X11 链接库走 conan 依赖（全部 ohpcd 已发布 OHOS armv8 binary，
        # W0 conan download 实测）。libxaw 传递拉入 libxt/libxmu/libxpm/
        # xorgproto（配方内 transitive_headers/transitive_libs）。
        self.requires("libxaw/1.0.14", transitive_headers=True, transitive_libs=True)
        # shape.h（X11/extensions/）在 libxext 包；libx11/libxcb/libxau 由
        # libxaw/libxext 传递拉入（libxmu force 钉 libx11/1.8.13，根上不可
        # 显式重复钉版本，否则图冲突）
        self.requires("libxext/6.4.0.1", transitive_headers=True, transitive_libs=True)
        # X-Face 解码（-DXFACE）
        self.requires("compface/1.5.2", transitive_headers=True, transitive_libs=True)

    def export_sources(self):
        # 模板合规（R22/conan-verify G1）：patches 为空数组时 no-op；
        # 若未来引入补丁，conandata.yml patches 即自动生效
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        # E002: /tmp 只读，conan get() 经 tempfile 展开归档，先钉可写 TMPDIR
        tmpdir = self._pin_writable_tmpdir()
        os.environ["TMPDIR"] = tmpdir
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------------ helpers

    def _pin_writable_tmpdir(self):
        """E002（readonly_tmp）：OHOS /tmp 只读。优先 HMBS/TMPDIR 注入，
        回退 build_folder/tmp（恒可写）。"""
        candidates = []
        for _var in ("HMBS_TMPDIR", "TMPDIR", "TMP", "TEMP"):
            _val = os.environ.get(_var, "")
            if _val and _val != "/tmp" and _val not in candidates:
                candidates.append(_val)
        for _cand in candidates:
            try:
                os.makedirs(_cand, exist_ok=True)
                import tempfile
                _fd, _p = tempfile.mkstemp(dir=_cand)
                os.close(_fd)
                os.unlink(_p)
                return _cand
            except Exception:  # noqa: BLE001
                continue
        _fb = os.path.join(self.build_folder or os.getcwd(), "tmp")
        os.makedirs(_fb, exist_ok=True)
        return _fb

    def _cc(self):
        """R33: 编译器从 conf 取，不可用时回退 PATH 探测（myman 同款）。"""
        try:
            compilers = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict)
            conf_cc = compilers.get("c") or compilers.get("cpp")
        except Exception:  # noqa: BLE001
            conf_cc = None
        if conf_cc and os.path.isfile(conf_cc) and os.access(conf_cc, os.X_OK):
            return conf_cc
        for _cand in (shutil.which("clang"), shutil.which("cc"),
                      shutil.which("aarch64-linux-ohos-clang")):
            if _cand and os.path.isfile(_cand):
                return _cand
        return conf_cc or "clang"

    def _prepend_toolchain_path(self):
        """CI worker PATH 缺工具链目录兜底（myman 同款）。"""
        cc = self._cc()
        toolchain_dir = os.path.dirname(cc) if cc else ""
        if not toolchain_dir or not os.path.isdir(toolchain_dir):
            return
        cur = os.environ.get("PATH", "")
        if toolchain_dir not in cur.split(os.pathsep):
            os.environ["PATH"] = toolchain_dir + os.pathsep + cur

    def _dep_flags(self):
        """聚合全部 conan 依赖的 include/lib 目录与链接库。

        注意：cpp_info.includedirs/libdirs 元素与 dep.package_folder 均可能
        为 None（components 聚合包/未实例化包），逐一判空跳过。
        """
        incdirs, libdirs, libs = [], [], []
        for dep in self.dependencies.values():
            info = dep.cpp_info
            pkg = dep.package_folder
            if not pkg:
                continue
            for d in list(info.includedirs or []):
                if not d:
                    continue
                p = os.path.join(pkg, d)
                if p not in incdirs:
                    incdirs.append(p)
            for d in list(info.libdirs or []):
                if not d:
                    continue
                p = os.path.join(pkg, d)
                if p not in libdirs:
                    libdirs.append(p)
            for l in (info.libs or []) + (info.system_libs or []):
                if l and l not in libs:
                    libs.append(l)
        return incdirs, libdirs, libs

    def _sign_elf(self, path):
        """ELF 代码签名（OHOS 拒绝未签名可执行文件，myman/xeyes 同款）。"""
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if os.path.exists(sign_tool):
            self.run(f'{objcopy} --remove-section .codesign "{path}" 2>/dev/null || true')
            self.run(f'{sign_tool} sign -inFile "{path}" -outFile "{path}" -selfSign 1')
        try:
            os.chmod(path, 0o755)
        except OSError:
            pass

    # -------------------------------------------------------------- build steps

    def build(self):
        cc = self._cc()
        self.output.info(f"xfaces cc resolved: {cc}")
        self._prepend_toolchain_path()
        os.environ["TMPDIR"] = self._pin_writable_tmpdir()
        os.environ["CONFIG_SHELL"] = "/bin/sh"
        os.environ["SHELL"] = "/bin/sh"
        # HMDFS getcwd 兜底：进程 cwd 固定到 build_folder 并预置 PWD
        try:
            os.chdir(self.build_folder)
        except OSError:
            self.output.warning("chdir(build_folder) failed; relying on PWD fallback")
        os.environ["PWD"] = self.build_folder

        incdirs, libdirs, _libs = self._dep_flags()
        src = self.source_folder
        objdir = os.path.join(self.build_folder, "objs")
        os.makedirs(objdir, exist_ok=True)

        # 宏定义对齐 Makefile.noimake 启用集（sound/netaudio 裁剪）；
        # -Drindex=strrchr：musl/bionic libc 无 rindex 遗留符号（face_binding.c/
        # mail_parse.c 使用），POSIX 等价 strrchr 原地替换，无行为差异
        apply_conandata_patches(self)  # 空补丁 no-op（conan-verify G1 合规）
        defs = "-DXPM -DSHAPE -DXFACE -DPOP -DLOOKUP_HOSTNAME -Drindex=strrchr"
        opt = "-O0 -g" if str(self.settings.build_type) == "Debug" else "-O2"
        cppflags = " ".join(f"-I{d}" for d in incdirs)
        objs = []
        for name in sorted(os.listdir(src)):
            if not name.endswith(".c") or name == "face_sound.c":
                continue
            obj = os.path.join(objdir, name[:-2] + ".o")
            self.run(f"{shlex.quote(cc)} {defs} {opt} {cppflags} -c "
                     f"-o {shlex.quote(obj)} {shlex.quote(os.path.join(src, name))}")
            objs.append(obj)

        # 链接序：Xaw→Xmu→Xt→Xpm→Xext→X11→compface（依赖序向后解析）
        ldflags = " ".join(f"-L{d}" for d in libdirs)
        link = (f"{shlex.quote(cc)} {' '.join(shlex.quote(o) for o in objs)} "
                f"-o {shlex.quote(os.path.join(objdir, 'xfaces'))} "
                f"{ldflags} -lXaw -lXmu -lXt -lXpm -lXext -lX11 -lcompface -lm "
                "-Wl,-rpath,'$ORIGIN'")
        self.run(link)

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        copy(self, "xfaces", os.path.join(self.build_folder, "objs"), bin_dir)
        # 应用资源文件（Xt resource 默认文件，运行期可选加载）
        copy(self, "XFaces.ad", self.source_folder,
             os.path.join(self.package_folder, "share", "xfaces"))
        self._sign_elf(os.path.join(bin_dir, "xfaces"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
