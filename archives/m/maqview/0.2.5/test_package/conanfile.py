#!/usr/bin/env python3
"""test_package — maqview 0.2.5 消费者验证（真实执行 + 无头 GL）。

设备即目标机（OHOS/aarch64 原生 build=host），所以测试二进制**真跑**而不是
只编译。测试分三块：

A. **真实执行打包出的二进制**（R34：测试必须实质依赖被测包）
   - `maqindex`（无参数）→ 退出码 1 + 打印 `Usage:`（maqmap_index_main.c:118
     `if (optind == argc) return usage();`，usage() 返回 1）。
   - `maqview`（无参数）→ 进程必须能**加载** libfreeglut-gles.so + libOSMesa +
     libglapi + libGLU + libEGL/libGLESv2，并跑到 freeglut 初始化 / usage 分支。
     main() 第一句是 `glutInit(&argc, argv)`（MainFrame.c:190）。本机无 X 显示，
     若 EGL 拿不到 display（fg_init_egl.c 的 `eglGetDisplay()` 返回
     EGL_NO_DISPLAY 会 fgError 退出），输出 `<No display available>` 且 rc=1
     —— 这是**允许**的（口径：无 X 显示时仅链接/测试，不要求真窗口）；
     被禁止的是 loader 的缺库/缺符号报错。若 EGL 可用，则走到
     `if(optind == argc) return maqview_usage();`（MainFrame.c:201）打印 Usage。
   - 被 L1e 破坏性反向验证移走 `bin/` 后，这些 `self.run` 会以
     “No such file” 失败 → 测试真正依赖被测包。

B. **无头桌面 GL 渲染**（test_gl_headless.cpp）：用 mesa 的 OSMesa 离屏上下文
   跑 maqview 同款固定管线入口（glBegin/glVertex/glOrtho/glMatrixMode…），对
   中心像素做具体数值断言。无 X display。

C. **制品断言**：每个打包 ELF 的 `readelf -S` 恰好 1 个 `.codesign` 段；
   `readelf -d` 的 DT_NEEDED 不含绝对路径/`../`。
"""
import glob
import os
import shlex
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.layout import basic_layout

GL_DEPS = ("mesa", "glu", "freeglut")
EXPECTED_BINS = ("maqview", "maqindex", "zrio", "maqindex_socks")
READELF_CANDIDATES = ("/data/service/hnp/bin/readelf", "readelf")


class MaqviewTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    # VirtualRunEnv：打包二进制的 soname 无 RUNPATH，运行期库搜索路径必须显式给出
    generators = "VirtualBuildEnv", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    # ── 编译无头 GL 消费者 ──────────────────────────────────────────────

    def build(self):
        mesa = self.dependencies.host["mesa"]
        include_dir = os.path.join(mesa.package_folder, "include")
        lib_dir = os.path.join(mesa.package_folder, "lib")
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        compiler = compilers.get("cpp") or os.environ.get("CXX") or "clang++"
        output = os.path.join(self.build_folder, "test_gl_headless")
        command = " ".join([
            shlex.quote(compiler),
            "-std=c++17",
            "-I%s" % shlex.quote(include_dir),
            shlex.quote(os.path.join(self.source_folder, "test_gl_headless.cpp")),
            "-L%s" % shlex.quote(lib_dir),
            "-lOSMesa",
            "-lglapi",
            *["-Wl,-rpath,%s" % shlex.quote(path)
              for path in [lib_dir] + self._sdk_runtime_dirs()],
            "-o %s" % shlex.quote(output),
        ])
        self.run(command, env="conanbuild")

    # ── 运行期库路径 ────────────────────────────────────────────────────

    def _runtime_dirs(self):
        dirs = []
        for dep in GL_DEPS:
            try:
                folder = self.dependencies.host[dep].package_folder
            except KeyError:
                continue
            libdir = os.path.join(folder, "lib")
            if os.path.isdir(libdir):
                dirs.append(libdir)
        dirs.extend(self._sdk_runtime_dirs())
        return list(dict.fromkeys(dirs))

    def _sdk_runtime_dirs(self):
        if str(self.settings.os) != "OHOS":
            return []
        sdk_roots = ["/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18"]
        sdk_roots.extend(sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*")))
        result = []
        for sdk_root in sdk_roots:
            native = os.path.join(sdk_root, "ohos", "native")
            candidates = [
                os.path.join(native, "llvm", "lib", "aarch64-linux-ohos", "c++"),
                os.path.join(native, "llvm", "lib", "aarch64-linux-ohos"),
                os.path.join(native, "sysroot", "usr", "lib", "aarch64-linux-ohos"),
            ]
            for candidate in candidates:
                if not os.path.isdir(candidate):
                    continue
                if (os.path.isfile(os.path.join(candidate, "libc++_shared.so"))
                        or os.path.isfile(os.path.join(candidate, "libz.so"))):
                    result.append(candidate)
            if result:
                break
        return list(dict.fromkeys(result))

    def _bash(self):
        return os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")

    def _run_capture(self, argv, log_name):
        """在显式 LD_LIBRARY_PATH 下跑 argv，返回 (rc, 合并输出)。"""
        log = os.path.join(self.build_folder, log_name)
        ldpath = ":".join(self._runtime_dirs())
        inner = ('export LD_LIBRARY_PATH=%s${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}; '
                 'exec %s'
                 % (shlex.quote(ldpath + ":"),
                    " ".join(shlex.quote(a) for a in argv)))
        cmd = "%s -c %s > %s 2>&1" % (shlex.quote(self._bash()),
                                      shlex.quote(inner), shlex.quote(log))
        rc = self.run(cmd, env="conanrun", ignore_errors=True)
        with open(log, encoding="utf-8", errors="replace") as handle:
            return rc, handle.read()

    # ── 测试 ────────────────────────────────────────────────────────────

    def test(self):
        pkg = self.dependencies.host["maqview"]
        bindir = os.path.join(pkg.package_folder, "bin")
        if not os.path.isdir(bindir):
            raise ConanException("package has no bin/ directory: %s" % bindir)

        # A. 打包二进制存在
        for name in EXPECTED_BINS:
            path = os.path.join(bindir, name)
            if not (os.path.isfile(path) and os.access(path, os.X_OK)):
                raise ConanException("missing packaged executable: %s" % path)

        # A. maqindex：真实执行 + 断言 usage 文本
        rc, text = self._run_capture([os.path.join(bindir, "maqindex")],
                                     "maqindex.out")
        self.output.info("maqindex rc=%d" % rc)
        if rc != 1 or "Usage" not in text:
            raise ConanException(
                "maqindex no-arg run unexpected: rc=%d output=%r" % (rc, text[:400]))

        # A. maqview：真实执行（触发 glutInit → 加载 GLUT/GL 栈）。
        #    注意：本机无 X 显示，若 freeglut 的 EGL 初始化拿不到 display
        #    （fg_init_egl.c 的 eglGetDisplay() 返回 EGL_NO_DISPLAY 会
        #    fgError 退出），进程会以 rc=1 打印 <No display available>。
        #    这是**允许**的（本任务口径：无 X 显示时仅链接/测试，不要求真
        #    窗口）。此处断言的是**动态加载**成功——不得出现 loader 的缺库/
        #    缺符号报错——且进程确实跑进了 freeglut 初始化或 usage 分支。
        rc, text = self._run_capture([os.path.join(bindir, "maqview")],
                                     "maqview.out")
        self.output.info("maqview rc=%d" % rc)
        loader_error = ("cannot open shared object" in text
                        or "error while loading shared libraries" in text
                        or "symbol not found" in text)
        if loader_error:
            raise ConanException(
                "maqview failed to load its GL/GLUT stack: %r" % text[:400])
        if "Usage" not in text and "freeglut" not in text:
            raise ConanException(
                "maqview neither printed usage nor reached freeglut init: "
                "rc=%d output=%r" % (rc, text[:400]))
        if rc != 1:
            raise ConanException(
                "maqview no-arg run exit code %d (expected 1): %r"
                % (rc, text[:400]))

        # B. 无头桌面 GL 渲染（具体像素断言）
        binary = os.path.join(self.build_folder, "test_gl_headless")
        rc, text = self._run_capture([binary], "test_gl_headless.out")
        self.output.info("test_gl_headless rc=%d" % rc)
        if rc != 0 or "PASS:" not in text or "colored_pixels=0" in text:
            raise ConanException(
                "headless GL render test failed: rc=%d output=%r" % (rc, text[:600]))
        self.output.info(text.strip())

        # C. 制品断言：.codesign 覆盖每个 ELF + DT_NEEDED 合理
        self._assert_packaged_elfs(pkg.package_folder)

    # ── 制品断言 ────────────────────────────────────────────────────────

    def _readelf(self):
        for candidate in READELF_CANDIDATES:
            if os.path.sep in candidate:
                if os.path.isfile(candidate):
                    return candidate
            else:
                for directory in os.environ.get("PATH", "").split(os.pathsep):
                    path = os.path.join(directory, candidate)
                    if os.path.isfile(path):
                        return path
        raise ConanException("readelf not found")

    def _elfs(self, root):
        found = []
        for dirpath, _dirs, files in os.walk(root):
            for name in files:
                path = os.path.join(dirpath, name)
                if os.path.islink(path):
                    continue
                with open(path, "rb") as handle:
                    if handle.read(4) != b"\x7fELF":
                        continue
                found.append(path)
        return sorted(found)

    def _assert_packaged_elfs(self, package_folder):
        readelf = self._readelf()
        elfs = self._elfs(package_folder)
        if not elfs:
            raise ConanException("no ELF artifact packaged")
        for elf in elfs:
            sections = subprocess.run([readelf, "-SW", elf],
                                      capture_output=True, text=True)
            if sections.returncode != 0:
                raise ConanException("readelf -SW failed: %s" % elf)
            count = sum(1 for line in sections.stdout.splitlines()
                        if ".codesign" in line)
            if str(self.settings.os) == "OHOS" and count != 1:
                raise ConanException(
                    "%s has %d .codesign section(s), expected exactly 1"
                    % (elf, count))

            dynamic = subprocess.run([readelf, "-d", elf],
                                     capture_output=True, text=True)
            if dynamic.returncode != 0:
                raise ConanException("readelf -d failed: %s" % elf)
            bad = [line.strip() for line in dynamic.stdout.splitlines()
                   if "(NEEDED)" in line and ("[/" in line or "[../" in line)]
            if bad:
                raise ConanException(
                    "%s has absolute/relative DT_NEEDED: %s" % (elf, bad))
            self.output.info("ELF ok: %s (.codesign=%d)"
                             % (os.path.relpath(elf, package_folder), count))
