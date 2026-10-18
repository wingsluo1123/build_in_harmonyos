import glob
import os
import shutil
import subprocess
from conan import ConanFile

class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "PkgConfigDeps", "VirtualRunEnv", "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # pangoxft.h → X11/Xlib.h → X11/X.h（来自 xorgproto）
        # pango 不传递 xorgproto（通过 libx11 间接依赖），需显式拉入
        self.requires("xorgproto/2025.1", override=True)

    def _pkgconfig(self, what, pc_name):
        """跑 pkg-config 取 --cflags 或 --libs。取不到返回空串，由调用方回退。"""
        env = dict(os.environ)
        env["PKG_CONFIG_PATH"] = self.generators_folder + os.pathsep + env.get("PKG_CONFIG_PATH", "")
        exe = shutil.which("pkg-config", path=env.get("PATH", os.defpath))
        if not exe:
            for _cand in ("/data/service/hnp/bin/pkg-config", "/usr/bin/pkg-config"):
                if os.path.isfile(_cand) and os.access(_cand, os.X_OK):
                    exe = _cand
                    break
        if not exe:
            return ""
        try:
            out = subprocess.run([exe, what, pc_name], capture_output=True,
                                 text=True, env=env, timeout=60)
            if out.returncode == 0 and out.stdout.strip():
                return out.stdout.strip()
        except (OSError, subprocess.SubprocessError):
            pass
        return ""

    def _pkgconfig_cflags(self, pc_name):
        out = self._pkgconfig("--cflags", pc_name)
        if out:
            self.output.info("test_package 用 pkg-config --cflags %s" % pc_name)
        else:
            self.output.warning("pkg-config --cflags %s 取不到，回退 cpp_info" % pc_name)
        return out

    def _gather_all_includes(self):
        """收集所有依赖（含传递）的 includedirs，去补全已知漏的路径。"""
        incs = []
        for _ref, _d in self.dependencies.items():
            for _p in _d.cpp_info.includedirs:
                incs.append("-I" + _p)
                if not os.path.isdir(_p):
                    continue
                for _name in sorted(os.listdir(_p)):
                    _sub = os.path.join(_p, _name)
                    if os.path.isdir(_sub) and any(
                            f.endswith((".h", ".hpp", ".hh", ".hxx"))
                            for f in os.listdir(_sub)):
                        incs.append("-I" + _sub)
        # 特殊：glibconfig.h 在 glib 的 lib/glib-2.0/include，cpp_info 可能漏
        _glib_dep = self.dependencies.get("glib")
        if _glib_dep:
            for _lp in _glib_dep.cpp_info.libdirs:
                _cfg = os.path.join(_lp, "glib-2.0", "include")
                if os.path.isdir(_cfg):
                    incs.append("-I" + _cfg)
        # 特殊：X11/X.h 在 xorgproto 包中，不通过 libx11 传递
        # 扫描 conan 缓存定位
        _xorg_inc = self._find_xorgproto_include()
        if _xorg_inc:
            incs.append("-I" + _xorg_inc)
        return " ".join(dict.fromkeys(incs))

    @staticmethod
    def _find_xorgproto_include():
        """扫描 conan 缓存找 xorgproto 的 include/X11 目录。"""
        _home = os.environ.get("CONAN_HOME", "")
        if not _home:
            _home = os.path.expanduser("~/.conan2")
        _pattern = os.path.join(_home, "p", "xorgp*", "p", "include")
        for _cand in sorted(glob.glob(_pattern)):
            # 必须验证 X11/X.h 真实存在（多个 revision 时排序靠前的可能为空包）
            if os.path.isfile(os.path.join(_cand, "X11", "X.h")):
                return _cand
        return ""

    def _compile_and_link(self, src, out_name, pc_name):
        """编译链接一个测试源文件，返回 (exit_cmd, env_dict)。
        pangoxft 的 pkg-config 不完整（缺 xorgproto 路径），强制用全量收集。
        其他包优先 pkg-config，回退 cpp_info。"""
        dep = self.dependencies["pango"].cpp_info
        if pc_name == "pangoxft":
            inc = self._gather_all_includes()
            self.output.info("pangoxft 测试强制用全量 include 收集（pkg-config 不完整）")
        else:
            inc = self._pkgconfig_cflags(pc_name)
            if not inc:
                inc = self._gather_all_includes()
                self.output.warning("pkg-config --cflags %s 取不到，回退全量收集" % pc_name)
        libdir = dep.libdirs[0]
        cc = os.environ.get("CC", "clang")
        std_flag = "-std=gnu99"
        libdirs = []
        for _ref, _d in self.dependencies.items():
            libdirs += _d.cpp_info.libdirs
        _pcl = self._pkgconfig("--libs", pc_name)
        _libs = _pcl.split() if _pcl else ["-l" + l for l in dep.libs]
        link = " ".join(["-L" + p for p in libdirs] + _libs
                        + ["-Wl,-rpath," + p for p in libdirs] + ["-ldl"])
        cmd = f"{cc} {std_flag} {src} -o {out_name} {inc} {link}"
        self.output.info("编译: %s" % cmd)
        self.run(cmd)
        return cmd

    def build(self):
        # 原有测试：pango 主库功能断言（泰文断行）
        self._compile_and_link("test.c", "test_probe", "pango")
        # 新增测试：xft 后端消费者用例
        self._compile_and_link("test_xft.c", "test_xft_probe", "pangoxft")

    def _runtime_env(self):
        """组装探针运行时 env。
        根因（实验确认）：libxft 预编译包自带的 .codesign 签名无效，
        OHOS 加载器对"签名无效"的库拒绝 exec 映射（dlopen → Permission denied）；
        而无 .codesign section 的库（如构建目录产物）可正常加载。
        处理：把全部依赖 so 复制到 conanhome 临时目录并剥离 .codesign，
        LD_LIBRARY_PATH 前置该目录，再叠加 conanrunenv 的完整闭包。"""
        import glob as _glob
        import shutil as _sh
        _home = getattr(self, "home_folder", None) or os.environ.get("CONAN_HOME") \
            or os.path.expanduser("~/.conan2")
        _rl = os.path.join(_home, "tmp-runtimelibs")
        if os.path.isdir(_rl):
            _sh.rmtree(_rl, ignore_errors=True)
        os.makedirs(_rl, exist_ok=True)
        # 1) 收集全部依赖（含 components）的 so，复制（跟随 symlink 保留 DT_NEEDED 名字）
        _libs = []
        for _ref, _d in self.dependencies.items():
            try:
                _cis = [_d.cpp_info] + list((_d.cpp_info.components or {}).values())
            except Exception:
                continue
            _pf = getattr(_d, "package_folder", None)
            for _ci in _cis:
                for _ld in (getattr(_ci, "libdirs", None) or []):
                    if not os.path.isabs(_ld) and _pf:
                        _ld = os.path.join(_pf, _ld)
                    if os.path.isdir(_ld):
                        _libs += sorted(_glob.glob(os.path.join(_ld, "*.so*")))
        for _f in dict.fromkeys(_libs):
            if os.path.isfile(_f):
                try:
                    _sh.copy(_f, os.path.join(_rl, os.path.basename(_f)))
                except OSError:
                    pass
        # 2) 修复 libXft 预编译包的两个问题（实验确认）：
        #    a) 自带 .codesign 签名无效 → OHOS 加载器 EACCES：先剥再 selfSign
        #    b) DT_NEEDED libxml2.so.16 但 0 个 xml 符号引用（构建污染）且
        #       conan 图无 libxml2 → patchelf 剥离该 NEEDED（安全：无符号依赖）
        _oc = "/data/service/hnp/bin/llvm-objcopy"
        _sg = "/data/service/hnp/bin/binary-sign-tool"
        _pe = "/data/service/hnp/bin/patchelf"
        for _so in sorted(_glob.glob(os.path.join(_rl, "*.so*"))):
            if os.path.islink(_so):
                continue
            if os.path.basename(_so).startswith("libXft.so"):
                # patchelf 剥离污染的 libxml2.so.16 NEEDED（失败可容忍，忽略返回码）
                subprocess.run([_pe, "--remove-needed", "libxml2.so.16", _so],
                               capture_output=True, timeout=60)
            # 剥旧签名（失败可容忍）→ selfSign 重签（必须成功，否则运行期 EACCES）
            subprocess.run([_oc, "--remove-section", ".codesign", _so],
                           capture_output=True, timeout=60)
            subprocess.run([_sg, "sign", "-inFile", _so, "-outFile", _so, "-selfSign", "1"],
                           capture_output=True, timeout=60, check=True)
        # 3) LD_LIBRARY_PATH = runtimelibs + conanrunenv 闭包
        env = dict(os.environ)
        _ldlp = []
        for _ef in _glob.glob(os.path.join(self.generators_folder, "conanrunenv-*.sh")):
            with open(_ef, encoding="utf-8") as _f:
                for _line in _f:
                    if _line.startswith("export LD_LIBRARY_PATH="):
                        _v = _line.split("=", 1)[1].strip().strip('"')
                        _ldlp += [p for p in _v.replace("\\ ", " ").split(":") if p]
        env["LD_LIBRARY_PATH"] = ":".join([_rl] + _ldlp)
        # 4) libthai 词典数据（conan 包 prefix 空导致内嵌 "//share/libthai" 不可达）
        _lt = self.dependencies.get("libthai")
        if _lt:
            _lt_data = os.path.join(_lt.package_folder, "share", "libthai")
            if os.path.isfile(os.path.join(_lt_data, "thbrk.tri")):
                env["LIBTHAI_DICTDIR"] = _lt_data
        return env

    def test(self):
        """【鸿蒙特有】真实运行消费者探针。
        本机即 OHOS arm64（host=build 同 profile），交叉产物原生可运行；
        此前"OHOS 跳过运行"系缺库报错的错误归因（真实根因：libxft 预编译包
        .codesign 签名无效 → OHOS 加载器 EACCES，见 _runtime_env）。"""
        import subprocess
        env = self._runtime_env()
        for _probe in ("./test_probe", "./test_xft_probe"):
            _r = subprocess.run([_probe], cwd=os.path.dirname(os.path.abspath(__file__)),
                                env=env, capture_output=True, text=True, timeout=120)
            self.output.info("运行 %s → exit=%d\n%s" % (_probe, _r.returncode,
                                                        _r.stdout.strip()[:400]))
            if _r.returncode != 0:
                self.output.error("%s 运行失败:\n%s" % (_probe, _r.stderr[-1500:]))
                raise Exception("%s 运行失败 exit=%d" % (_probe, _r.returncode))
