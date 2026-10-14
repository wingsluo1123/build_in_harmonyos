#!/usr/bin/env python3
"""Conan recipe for greenlet 3.5.6 — lightweight in-process concurrent programming.

HarmonyOS PC adaptation. Unlike the other Python packages in this archive
(markupsafe / itsdangerous / pycparser), greenlet is **not** pure Python: it is
a single C++ extension module (``_greenlet``) built from ~20 ``.cpp`` files, and
upstream provides **no pure-Python fallback** — ``greenlet/__init__.py`` imports
from ``._greenlet`` unconditionally. It therefore has to be compiled, and the
resulting ``.so`` is tied to the build host's CPython ABI/arch, exactly like
lxml/pillow/cppy in this archive.

Two build details that were measured, not assumed:

* **``-lpython3.12`` is mandatory.** musl does not export the main
  executable's Python symbols, so linking without it produces a module that
  links fine but fails at import time with::

      ImportError: Error relocating .../_greenlet...so: _Py_IsFinalizing: symbol not found

  The symbol lives in ``libpython3.12.so``; linking it explicitly fixes the
  module. Same conclusion as lxml (``LDFLAGS="-fuse-ld=bfd -L{py_lib}
  -lpython3.12"``) and pillow (its header: "musl does not export main exe
  symbols -> -lpython3.12"). **GNU ld.bfd is used for the link step** for the
  same reason as those packages.

* **Signing IS needed here.** The module is linked with GNU ld.bfd (required for
  ``-lpython3.12``), and bfd output is not auto-signed the way lld's is; an ELF
  without a ``.codesign`` section is refused by the HMDFS loader
  (``E212 Permission denied``). ``build()`` therefore signs the three in-place
  test extensions before pytest, and ``package()`` signs the packaged module —
  the same treatment lxml 6.1.1 / pillow 10.4.0 apply.

Upstream test suite: ``src/greenlet/tests/__init__.py`` and ``leakcheck.py`` do
bare ``import psutil`` / ``import objgraph`` (no try/except). Both were
**unpublished earlier**, so the suite could not be collected; they are now
published on ohpcd, so ``build_requirements()`` declares them and the suite runs
in full — see ``_run_upstream_tests``. The two import-optionality patches are
retained purely as a degradation path.

The suite is a **hard gate**, not advisory: if it cannot be collected, or
pytest exits non-zero, ``build()`` raises rather than warning. Otherwise the
"166 passed / 0 failed" figures recorded in notes.md and MANIFEST.yml could
become false silently the first time upstream regresses. Same contract as the
other recipes here (biopython / saunafs).
"""
import os
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class GreenletConan(ConanFile):
    name = "greenlet"
    version = "3.5.6"
    description = "Lightweight in-process concurrent programming"
    license = "MIT AND PSF-2.0"
    homepage = "https://greenlet.readthedocs.io/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # NOT "python-require": that type forbids depending on a typed library, and
    # this recipe must require python/3.12.9 (headers + libpython3.12.so for the
    # extension build), which transitively brings libffi as a static-library:
    #   ERROR: Package 'greenlet/3.5.6' with type 'python-require' cannot have
    #          a 'static-library' dependency to 'libffi/3.5.2'
    # The archive's other compiled Python extensions do the same — lxml 6.1.1
    # uses package_type = "library" with requires("python/3.12.9").
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    # Required by package_type "library" (else: "Package type is 'library', but
    # no 'shared' option declared"). Mirrors lxml 6.1.1 exactly — the artifact
    # is in fact a CPython extension module (.so), which is a shared object.
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Headers (Python.h) and libpython3.12.so for the extension build; the
        # same dependency the other C-extension Python packages declare.
        self.requires("python/3.12.9")

    def build_requirements(self):
        """上游测试期可选依赖（现已全部发布到 ohpcd）。

        上游 ``pyproject.toml [project.optional-dependencies].test`` 声明
        ``objgraph`` / ``psutil``（另有 ``setuptools``，本配方直接编译扩展、
        不经 setup.py，故不声明）。早期两者未发布，只能退化为
        「相关用例 SkipTest + 理由」——这正是 rule 4 拒绝的「缺依赖」处置。
        现两者均已发布，故按 R36 正常声明依赖，让套件**真正跑起来**。

        用 ``tool_requires``（build 上下文）而非 ``test_requires``：pytest 在
        ``build()`` 内执行，测试依赖属构建期工具链；两者的 ``buildenv_info``
        都声明了各自的 site-packages，由 ``VirtualBuildEnv`` 聚合进构建环境
        （见 ``_run_upstream_tests``）。走 build 上下文还可避免把依赖的 host
        依赖链并入本包图而引发版本冲突（objgraph 配方记录过同族坑）。
        """
        self.tool_requires("psutil/7.2.2")
        self.tool_requires("objgraph/3.6.2")
        # ★ pytest 本身也必须来自制品，不能指望运行 conan 的那个解释器自带。
        # CI 实测（#10408）：构建由 ``/data/service/hnp/bin/python3`` 驱动，该
        # 解释器**不含 pytest**，于是 ``python3 -m pytest`` 报
        # ``No module named pytest``、收集 rc=1 —— 在本配方把套件改为硬门禁
        # 之前，这条路径一直是 ``warn + return`` 静默跳过，即**CI 上从未真正
        # 跑过上游套件**（notes/MANIFEST 的通过数只在本地成立）。
        # ohpcd 已有 pytest/9.1.1 制品（含 pytest 模块与 iniconfig/pluggy/
        # packaging/pygments 依赖闭包），故按 R36 正常声明；不走 pip 镜像，
        # 版本被锁进依赖图，可复现、可审计。
        self.tool_requires("pytest/9.1.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def _py_paths(self):
        py = self.dependencies["python"]
        pkg = py.package_folder
        return {
            "pkg": pkg,
            "bin": os.path.join(pkg, "bin", "python3.12"),
            "lib": os.path.join(pkg, "lib"),
            "inc": os.path.join(pkg, "include", "python3.12"),
        }

    def _resolve_tool(self, configured, fallback_name):
        """Resolve a compiler executable, tolerating an unusable value.

        ``tools.build:compiler_executables`` may supply a *bare* name (CI does:
        ``clang``), whose directory is not on ``PATH`` — honouring it verbatim
        aborts with ``FileNotFoundError: 'clang'``. A value is therefore used
        only when it resolves (as an existing path, or via ``PATH``); otherwise
        the usual absolute fallbacks are tried.
        """
        fallbacks = (
            f"/data/service/hnp/bin/{fallback_name}",
            f"/storage/Users/currentUser/usr/local/bin/{fallback_name}",
            f"/usr/bin/{fallback_name}",
        )
        for cand in (configured, fallback_name) + fallbacks:
            if not cand:
                continue
            if os.path.sep in cand:
                if os.path.isfile(cand) and os.access(cand, os.X_OK):
                    return cand
                continue
            found = shutil.which(cand)
            if found:
                return found
        raise ConanException(
            f"could not resolve a usable '{fallback_name}' compiler "
            f"(configured={configured!r}; tried {fallbacks})")

    def _py_ext_suffix(self, p):
        """Return the interpreter's EXT_SUFFIX for the extension modules."""
        res = subprocess.run(
            [p["bin"], "-c",
             "import sysconfig; print(sysconfig.get_config_var('EXT_SUFFIX'))"],
            capture_output=True,
            env={**os.environ,
                 "LD_LIBRARY_PATH": p["lib"] + os.pathsep
                                    + os.environ.get("LD_LIBRARY_PATH", "")},
            timeout=120)
        suffix = res.stdout.decode(errors="ignore").strip()
        if res.returncode != 0 or not suffix:
            raise ConanException(
                "could not determine EXT_SUFFIX from the python dependency: "
                + res.stderr.decode(errors="ignore")[:400])
        return suffix

    def build(self):
        # NOTE: patches are applied in source() only. Calling
        # apply_conandata_patches() a second time here re-applied them on top of
        # the already-patched tree, which CI reported as
        #   WARN: .../0002-tests-objgraph-optional.patch: hunk no.1 doesn't match
        #   ... actual: b'try:'
        #   WARN: ... already patched  b'src/greenlet/tests/leakcheck.py'
        # Not fatal (git apply fuzzes through it), but it means the patch layer
        # is not idempotent and would also mask a genuinely failing patch.
        if not os.path.isdir(os.path.join(self.source_folder, "src", "greenlet")):
            raise ConanException("src/greenlet package directory not found")

        p = self._py_paths()
        py_lib = p["lib"]

        # Compiler executables come from the profile (R33). A bare name is only
        # honoured when it actually resolves: CI exports bare names whose
        # directory is not on PATH.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = self._resolve_tool(compilers.get("c"), "clang")
        cxx = self._resolve_tool(compilers.get("cpp"), "clang++")

        lib_dirs = [py_lib]
        inc_dirs = [p["inc"]]
        for dep in self.dependencies.values():
            pf = dep.package_folder
            if not pf:
                continue
            lib_dirs.append(os.path.join(pf, "lib"))
            inc_dirs.append(os.path.join(pf, "include"))
        ld_path = os.pathsep.join([d for d in lib_dirs if d])
        inc_path = os.pathsep.join([d for d in inc_dirs if d])
        # ★ 记下来给 _run_upstream_tests 用。扩展是用 `-L<py_lib> -lpython3.12`
        #   链接的，产物带 `NEEDED libpython3.12.so.1.0` 且**没有 RUNPATH**
        #   （实测 llvm-readelf -d 无 RPATH/RUNPATH）。因此**运行期必须**把同一批
        #   lib 目录放进 LD_LIBRARY_PATH——编译期有（env_prefix），pytest 期原先
        #   没有，这就是收集阶段 15 个 import 错误（0 collected）的根因。
        self._ld_path = ld_path

        # Build the three extension modules **directly**, without setuptools.
        #
        # setup.py imports setuptools at module level, and setuptools is not
        # obtainable in this build environment:
        #   · the conan python package ships none (its site-packages holds only
        #     README.txt);
        #   · CI has no copy either — measured, all five candidates were
        #     probed and rejected:
        #       candidate without setuptools: <ci>/lib/python3.12/site-packages
        #       candidate without setuptools: <conan python>/…/site-packages
        #       candidate without setuptools: ~/.local/lib/python3.12/site-packages
        #       candidate without setuptools: ~/.opendesk/interpreters/pip-global
        #       candidate without setuptools: ~/usr/local/lib/python3.12/site-packages
        # A previous revision borrowed a host copy via PYTHONPATH; that only ever
        # worked on the build machine, which is why CI #10488 died with
        # "No module named 'setuptools'".
        #
        # Compiling directly is what archives/a/aggdraw/1.4.1 does for the same
        # reason, and it removes the dependency outright. The commands mirror the
        # Extension objects setup.py would have produced: greenlet.cpp (C++),
        # plus the two C/C++ test extensions under greenlet.tests.
        #
        # -lpython3.12 + -fuse-ld=bfd are both required: musl does not export the
        # main executable's Python symbols, and the module needs _Py_IsFinalizing
        # from libpython3.12.so — otherwise it links but fails at import with
        # "Error relocating ... _Py_IsFinalizing: symbol not found".
        ext_suffix = self._py_ext_suffix(p)
        src_dir = os.path.join(self.source_folder, "src", "greenlet")
        test_dir = os.path.join(src_dir, "tests")
        env_prefix = (f'export LD_LIBRARY_PATH="{ld_path}" && '
                      f'export LIBRARY_PATH="{ld_path}" && ')

        def compile_ext(compiler, source, out_path, cxx_std=False):
            flags = f'-shared -fPIC -O2{" --std=c++11" if cxx_std else ""}'
            self.run(
                env_prefix
                + f'"{compiler}" {flags} -I"{p["inc"]}" -I"{src_dir}" '
                f'"{source}" -L"{py_lib}" -lpython3.12 -fuse-ld=bfd '
                f'-o "{out_path}"',
                cwd=self.source_folder)

        built = []
        main_so = os.path.join(src_dir, f"_greenlet{ext_suffix}")
        compile_ext(cxx, os.path.join(src_dir, "greenlet.cpp"), main_so,
                    cxx_std=True)
        built.append(main_so)

        if os.path.isdir(test_dir):
            for name, compiler, cxx_std in (
                ("_test_extension", cc, False),
                ("_test_extension_cpp", cxx, True),
            ):
                src_name = (name + (".cpp" if cxx_std else ".c"))
                out = os.path.join(test_dir, f"{name}{ext_suffix}")
                compile_ext(compiler, os.path.join(test_dir, src_name), out,
                            cxx_std=cxx_std)
                built.append(out)

        missing = [b for b in built if not os.path.isfile(b)]
        if missing:
            raise ConanException(
                f"direct compilation produced no output for: {missing}")
        self.output.info(
            f"built extension(s): {[os.path.basename(b) for b in built]}")

        # Sign the *in-place* extension modules before running the suite. The
        # build-time modules are bfd-linked and unsigned, and HMDFS refuses to
        # dlopen an ELF without a .codesign section, so pytest would abort at
        # collection with e.g.
        #   ImportError: Error loading shared library .../_greenlet...so: Permission denied
        # (This is why the suite could never get past collection even with the
        # psutil/objgraph imports made optional.)
        #
        # All three modules matter: greenlet itself plus the two C/C++ test
        # extensions (greenlet.tests._test_extension and _test_extension_cpp) —
        # without them two test files cannot be collected at all.
        self._sign_extensions(built)

        self._run_upstream_tests()

    def _sign_extensions(self, paths):
        """Add a .codesign section to the given ELF modules (HMDFS requirement).

        Kept as one helper so build() and package() cannot drift apart: the
        build-time copy is signed for pytest, and the packaged copy is signed
        again in package() because conan's ``copy`` invalidates the signature.
        """
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if not os.path.isfile(sign_tool):
            self.output.warning(
                f"{sign_tool} not found — the extension will fail to dlopen on "
                "HMDFS (E212)")
            return
        for so in paths:
            if not os.path.isfile(so):
                continue
            if os.path.isfile(objcopy):
                self.run(f'"{objcopy}" --remove-section .codesign "{so}" '
                         f'2>/dev/null || true')
            self.run(f'"{sign_tool}" sign -inFile "{so}" '
                     f'-outFile "{so}.signed" -selfSign 1')
            if os.path.isfile(so + ".signed"):
                os.replace(so + ".signed", so)
                os.chmod(so, 0o755)
        self.output.info(f"signed extension module(s): {[os.path.basename(p) for p in paths]}")

    def _run_upstream_tests(self):
        """Run the upstream pytest suite and report the real result (R51).

        Three things had to be fixed for the suite to actually run here — the
        first was discovered from the CI report, the other two only surfaced
        once the suite could be collected:

        1. ``tests/__init__.py:17`` did a bare ``import psutil`` at module level.
           That *test-only, optional* probe aborted collection of the whole
           suite.  (psutil was also unpublished back then, so it could not be
           declared as a dependency at all; it is on ohpcd now.)
           -> ``patches/0001-tests-psutil-optional.patch``
        2. Same class of bug for ``objgraph``, at *two* sites:
           ``tests/leakcheck.py:32`` (imported by ``tests/__init__.py:33``) and
           ``tests/test_cpp.py:6``. Fixing only the first left collection still
           failing on the second.
           -> ``patches/0002-tests-objgraph-optional.patch``
        3. The extension modules are bfd-linked and unsigned at build time, and
           HMDFS refuses to dlopen an ELF with no ``.codesign`` section, so
           collection died with ImportError/Permission denied even with both
           patches applied. ``build()`` now signs all three modules (greenlet
           plus the two C/C++ test extensions) before invoking pytest.

        Both patches keep upstream's own semantics: the affected measurements
        raise ``unittest.SkipTest`` instead of fabricating values, so no
        assertion can pass on made-up data.

        Test-time dependencies (``objgraph``, ``psutil``) now come from
        ``build_requirements()`` as ``tool_requires``; their site-packages are
        prepended to PYTHONPATH below.  The two patches remain as the
        degradation path should a dependency ever be unavailable.

        **Why declare them instead of skipping the affected tests**: upstream
        declares them in ``pyproject.toml [project.optional-dependencies].test``.
        Without them, ``tests/__init__.py``'s ``wrap_refcount`` (which wraps
        *every* test method) makes the leakcheck decorator skip essentially the
        whole suite — an earlier state measured 3 passed / 168 skipped, which is
        no verification at all. Two ways out exist:

          a) set upstream's own ``GREENLET_SKIP_LEAKCHECKS=1`` to disable the
             leak checks entirely (what this recipe used to do), or
          b) provide objgraph so ``wrap_refcount`` works and the leak checks
             actually run.

        This recipe takes (b): it is strictly stronger evidence, since the leak
        measurements are a real detection path rather than a bypassed one.
        Should a dependency be unavailable, the affected tests fall back to
        SkipTest via the patches above and the counts reported below will show
        it — the degradation is visible, never masked.
        """
        tests_dir = os.path.join(self.source_folder, "src", "greenlet", "tests")
        if not os.path.isdir(tests_dir):
            self.output.warning("upstream tests not found, skipping pytest")
            return
        # ★ 跑套件的解释器必须与**编译扩展**的那个一致。
        #   扩展是 `-I<conan python include> … -L<conan python lib> -lpython3.12
        #   -fuse-ld=bfd` 编出来的，其 `NEEDED libpython3.12.so.1.0` 就是 conan
        #   python 包里的那一个。此前这里用 ``sys.executable``（CI 上是
        #   ``/data/service/hnp/bin/python3``）跑，虽然已把 conan python 的 lib
        #   放进 LD_LIBRARY_PATH，却让**宿主解释器**去加载另一个构建的 libpython，
        #   解释器自身先起不来（CI #82360 实测，rc=127）：
        #     Error loading shared library libpython3.12.so.1.0:
        #       (needed by /data/service/hnp/bin/python3)
        #     Error relocating /data/service/hnp/bin/python3:
        #       Py_BytesMain: symbol not found
        #   注意这与先前"扩展导入失败（0 collected / 15 errors）"是**两种**症状：
        #   前者解释器根本没起来，后者解释器起来了但 import 扩展失败。改用 conan
        #   python 后解释器与扩展来源统一，LD_LIBRARY_PATH 也只需服务它们自己。
        _py = self._py_paths()["bin"]
        py = _py if os.path.isfile(_py) else sys.executable
        if py != _py:
            self.output.warning(
                "[greenlet] conan python interpreter %s not found; falling back "
                "to %s — the built extension was linked against the former's "
                "libpython, so the run may fail to load it" % (_py, py))
        env = dict(os.environ)
        env["PYTHONPATH"] = os.path.join(self.source_folder, "src")
        env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
        # ★ 运行期必须补 LD_LIBRARY_PATH。扩展是用 `-L<py_lib> -lpython3.12
        #   -fuse-ld=bfd` 链接的，产物实测带
        #     NEEDED libpython3.12.so.1.0 / libc++_shared.so / libc.so
        #   且**没有 RUNPATH**（llvm-readelf -d 无 RPATH/RUNPATH 条目）。编译期
        #   由 env_prefix 显式设了 LD_LIBRARY_PATH，但此处 env 取自 os.environ——
        #   配方自己的 os.environ 里并没有它（实测 LD_LIBRARY_PATH 为 unset），
        #   于是 pytest 子进程导入扩展时加载器找不到 libpython3.12.so.1.0。
        #   症状：**所有**测试文件 import 失败 → 15 errors / 0 collected
        #   （CI #10408 实测；0.24s 即结束，符合"导入阶段就挂"的特征）。
        #   注意不能用 `os.pathsep.join` 覆盖掉调用方已有的值，故前置再拼接。
        _ld = getattr(self, "_ld_path", "") or ""
        _existing = os.environ.get("LD_LIBRARY_PATH", "")
        if _ld:
            env["LD_LIBRARY_PATH"] = os.pathsep.join(
                [p for p in (_ld, _existing) if p])
        # 上游声明的测试期可选依赖（pyproject.toml [project.optional-dependencies].test
        # = objgraph, psutil）：现由 build_requirements() 以 tool_requires 声明，
        # 此处把两个制品的 site-packages 前置到 PYTHONPATH。
        #
        # 为什么值得引入：
        #   * 不引入时 4 个测试因 `objgraph is None` / `psutil is None` 走 SkipTest；
        #     引入后这些测试**真正执行**（实测 psutil×3 由 skipped 转 passed，
        #     leak 测量从"整体跳过"变为真跑）。
        #   * 引入 objgraph 后，tests/__init__.py:72 的 wrap_refcount 不再因
        #     objgraph 缺失而 skip 整个套件，故**无需再覆盖上游开关**
        #     GREENLET_SKIP_LEAKCHECKS（见下）。
        #
        # 为什么改用 conan 制品（build_requirements 的 tool_requires）而不是
        # 原先的 pip 临时安装：
        #   * 依赖由 conan 解析**可复现、可审计**——版本被锁进依赖图，而不是每次
        #     构建去镜像取「当时最新」，且符合 R36「依赖须在制品仓」；
        #   * pip 路线把测试依赖装进**全局 site-packages**（--break-system-packages），
        #     污染构建环境且不可回滚；conan 制品则隔离在缓存中。
        # 实测澄清（勿再传播相反的想当然结论）：平台镜像的
        # psutil-7.2.2-cp312-cp312-ohos_aarch64.whl **本身已带 .codesign 段**
        # （llvm-readelf -S | grep -c codesign = 1），可直接 import 并调用其
        # C 扩展（psutil.Process().memory_full_info().uss 实测有值）。
        # 即**签名不是**改用 conan 制品的理由——可复现/可审计/R36 才是。
        _dep_sites = []
        _resolved = []
        # ★ 遍历 build 上下文的**全部**依赖，而不是硬编码 ("psutil","objgraph")。
        # 原因：pytest 自身也是 tool_requires，且它带 iniconfig / pluggy /
        # pygments / packaging 依赖闭包；漏掉任何一个，pytest 都起不来
        # （CI 实测 `No module named pytest`、随后 `No module named pygments`）。
        # ★ items() 的键是 **Requirement 对象**，不是字符串（conan 2.29
        #   internal/model/dependencies.py：`require.ref.name` 才拿得到包名）。
        #   Requirement 未实现 `<`，故不能直接 sorted()——CI 实测
        #     TypeError: '<' not supported between instances of 'Requirement'
        # ★ 路径**不能写死** `lib/python3.12/site-packages`：本图里 pytest 用
        #   `lib/python3.12/site-packages`，而 pygments 用
        #   `lib/python/site-packages`（无版本号）。写死版本的后果正是
        #   pygments 被静默漏掉 → `ModuleNotFoundError: No module named
        #   'pygments'`（CI #10408 实测）。故此处按 glob 匹配两种布局。
        import glob as _glob
        _build_items = []
        for _require, _dep in self.dependencies.build.items():
            _name = getattr(getattr(_require, "ref", None), "name", None) \
                or str(_require)
            _build_items.append((_name, _dep))
        for _name, _dep in sorted(_build_items, key=lambda kv: kv[0]):
            if _name in ("python",):
                continue
            _pf = getattr(_dep, "package_folder", None)
            if not _pf:
                continue
            _sites = sorted(_glob.glob(os.path.join(_pf, "lib", "python*",
                                                    "site-packages")))
            if _sites:
                _dep_sites.extend(_sites)
                _resolved.append(_name)
        for _req in ("pytest", "psutil", "objgraph"):
            if _req not in _resolved:
                self.output.warning(
                    "upstream pytest: test dependency %s has no usable "
                    "site-packages in the build context — the suite may not "
                    "run (not masked: the collection gate below will fail "
                    "loudly rather than report an unrun suite as passing)" % _req)
        if _dep_sites:
            self.output.info(
                "upstream pytest: build-context site-packages injected: %s"
                % sorted(_resolved))
        env["PYTHONPATH"] = os.pathsep.join(
            [self.source_folder + "/src"] + _dep_sites
            + [p for p in os.environ.get("PYTHONPATH", "").split(os.pathsep) if p])
        # NOTE: 原先此处设置 env["GREENLET_SKIP_LEAKCHECKS"] = "1" 以规避
        # 「3 passed / 168 skipped」的无效验证。装了 objgraph 后该规避不再需要
        # ——leak 检查本身就是一条有效的检测路径，覆盖它反而削弱证据强度。
        # 若依赖安装失败（objgraph 缺失），该 env 闸缺失会使套件大量 skip；
        # 届时下方 collector 预检与计数会如实反映出来（不掩盖）。
        # Repair the platform's broken os.popen before pytest starts.
        #
        # python/3.12.9 patch 0014 (_harmonyos_compat.py) wraps os.popen to use
        # subprocess, but passes ``text=True`` AND then wraps the (already text)
        # ``proc.stdout`` in ``io.TextIOWrapper`` a second time. The double
        # decode makes ``read()`` raise
        #   TypeError: can't concat str to bytes
        # on every call. Upstream ``tests/test_version.py:36`` calls os.popen to
        # run ``setup.py --version``; the TypeError surfaces as a test *failure*
        # (not a skip), so the suite can never reach 100% on this platform.
        #
        # This is a platform defect, not a greenlet or dependency problem: with
        # the wrapper corrected the very same test passes. We inject the fix via
        # a sitecustomize shim on PYTHONPATH, which repairs the environment
        # without touching a single upstream test file.
        _shim = os.path.join(self.build_folder, "_popen_shim")
        os.makedirs(_shim, exist_ok=True)
        with open(os.path.join(_shim, "sitecustomize.py"), "w") as _fh:
            _fh.write(
                "import os, subprocess\n"
                "_orig = os.popen\n"
                "def _fixed(cmd, mode='r', buffering=-1):\n"
                "    if mode != 'r':\n"
                "        return _orig(cmd, mode, buffering)\n"
                "    p = subprocess.Popen(cmd, shell=True,\n"
                "                         stdout=subprocess.PIPE,\n"
                "                         stderr=subprocess.STDOUT, text=True)\n"
                "    return p.stdout\n"
                "os.popen = _fixed\n"
            )
        env["PYTHONPATH"] = os.pathsep.join(
            [_shim, env["PYTHONPATH"]])
        self.output.info("upstream pytest: os.popen platform defect repaired via sitecustomize shim")

        # Preflight: the suite must be *collectable*. If it is not, fail the
        # build — an uncollectable suite means nothing was verified, and
        # continuing would let the "166 passed / 0 failed" figure recorded in
        # notes.md / MANIFEST.yml drift away from reality without any signal.
        # Same hard-fail contract as the other recipes in this archive
        # (biopython / saunafs refuse to report a pass on a failed suite).
        try:
            collect = subprocess.run(
                [py, "-m", "pytest", "src/greenlet/tests", "-q",
                 "--collect-only", "--assert=plain", "-p", "no:cacheprovider"],
                cwd=self.source_folder, env=env,
                capture_output=True, timeout=600)
        except Exception as e:
            raise ConanException(
                f"upstream test collection probe could not run: {e}")
        cout = (collect.stdout + collect.stderr).decode(errors="ignore")
        if collect.returncode != 0:
            # ★ 打印**每个错误的首个 traceback**，而不是尾部若干行。
            #   上一次 CI 失败时，尾部 12 行恰好只是 `ERROR src/.../test_*.py`
            #   清单与 "Interrupted: 15 errors"，真正点名的
            #   `ImportError: ... symbol not found / cannot open shared object`
            #   被截掉了，导致只能靠猜（白跑一轮）。此处按 pytest 的分隔线切块，
            #   取每块的前 12 行，最多 4 块——足够看到异常类型与缺失的库。
            _blocks = [b for b in cout.split("\n_ _ _ _") if "E " in b or "Error" in b]
            _picked = []
            for _b in _blocks[:4]:
                _picked.append("\n".join(_b.strip().splitlines()[:12]))
            _detail = "\n---\n".join(_picked) or "\n".join(cout.splitlines()[:40])
            raise ConanException(
                "upstream tests are not collectable (rc=%d) — refusing to "
                "report a pass; the suite must actually run for this package to "
                "count as verified. interpreter=%s\nLD_LIBRARY_PATH=%s\n"
                "First error(s):\n%s"
                % (collect.returncode, py, env.get("LD_LIBRARY_PATH", ""),
                   _detail))
        ncollected = sum(1 for ln in cout.splitlines()
                         if "::" in ln and "test" in ln)
        if ncollected <= 0:
            raise ConanException(
                "upstream collection reported 0 test items — refusing to report "
                "a pass (an empty run is not a verification). Tail:\n%s"
                % "\n".join(cout.strip().splitlines()[-12:]))
        self.output.info(f"upstream tests collected: {ncollected} test items")

        try:
            res = subprocess.run(
                [py, "-m", "pytest", "src/greenlet/tests", "-q",
                 "--assert=plain", "-p", "no:cacheprovider"],
                cwd=self.source_folder, env=env,
                capture_output=True, timeout=1200)
        except Exception as e:
            raise ConanException(f"upstream pytest could not run: {e}")
        out = (res.stdout + res.stderr).decode(errors="ignore").strip()
        # Surface skip reasons for the optional test deps so they stay visible.
        for ln in out.splitlines():
            low = ln.strip().lower()
            if ln.strip().startswith("SKIPPED") and (
                    "psutil" in low or "objgraph" in low):
                self.output.info(f"  {ln.strip()}")
        summary = [ln for ln in out.splitlines() if ln.strip()][-1:] or ["n/a"]
        self.output.info(f"upstream pytest: {summary[0]}")
        # Hard gate (R51/R9): a non-zero pytest exit means the recorded pass
        # counts no longer hold, so the build must fail rather than warn —
        # a warning-only path would silently turn "0 failed" into a false
        # statement in the shipped notes.
        if res.returncode != 0:
            raise ConanException(
                "upstream pytest failed (rc=%d) — refusing to report a pass. "
                "Tail:\n%s"
                % (res.returncode,
                   "\n".join(out.strip().splitlines()[-12:])))
        self.output.info("upstream pytest: suite passed")

    def package(self):
        py_ver = "python3.12"
        site = os.path.join(self.package_folder, "lib", py_ver, "site-packages")
        pkg_dst = os.path.join(site, "greenlet")
        src = os.path.join(self.source_folder, "src", "greenlet")
        os.makedirs(pkg_dst, exist_ok=True)

        # .py files + the compiled extension (top level of the package)
        for entry in sorted(os.listdir(src)):
            fpath = os.path.join(src, entry)
            if os.path.isdir(fpath):
                continue
            if entry.endswith((".cpp", ".hpp", ".h", ".c", ".pyi")):
                continue
            shutil.copy2(fpath, os.path.join(pkg_dst, entry))

        # platform/ subpackage holds .h and the (empty) __init__.py
        plat_src = os.path.join(src, "platform")
        if os.path.isdir(plat_src):
            plat_dst = os.path.join(pkg_dst, "platform")
            os.makedirs(plat_dst, exist_ok=True)
            init_py = os.path.join(plat_src, "__init__.py")
            if os.path.isfile(init_py):
                shutil.copy2(init_py, os.path.join(plat_dst, "__init__.py"))

        if not os.path.isfile(os.path.join(pkg_dst, "__init__.py")):
            raise ConanException(f"greenlet package missing under {pkg_dst}")
        exts = [f for f in os.listdir(pkg_dst) if f.endswith(".so")]
        if not exts:
            raise ConanException(f"greenlet extension missing under {pkg_dst}")

        # Sign the extension module. Without a .codesign section, HMDFS refuses
        # to dlopen the module and Python reports:
        #   ImportError: Error loading shared library .../_greenlet...so: Permission denied
        # Two reasons the section is missing by now:
        #   1. this recipe links with GNU ld.bfd (needed for -lpython3.12), and
        #      bfd output is not auto-signed (unlike lld, per pillow's notes);
        #   2. conan's copy() invalidates an existing ELF signature.
        # Measured: unsigned -> 0 .codesign sections + Permission denied;
        # after signing -> 1 section and import/switch work. Same treatment as
        # lxml 6.1.1 / pillow 10.4.0 in this archive.
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if os.path.isfile(sign_tool):
            for name in exts:
                so = os.path.join(pkg_dst, name)
                if os.path.isfile(objcopy):
                    self.run(f'"{objcopy}" --remove-section .codesign "{so}" '
                             f'2>/dev/null || true')
                self.run(f'"{sign_tool}" sign -inFile "{so}" '
                         f'-outFile "{so}.signed" -selfSign 1')
                if os.path.isfile(so + ".signed"):
                    os.replace(so + ".signed", so)
                    os.chmod(so, 0o755)
            self.output.info(f"signed extension module(s): {exts}")
        else:
            self.output.warning(
                f"{sign_tool} not found — the extension will fail to dlopen on "
                "HMDFS (E212) and only the ELF-verification fallback can run")

    def package_info(self):
        site = os.path.join(self.package_folder, "lib", "python3.12",
                            "site-packages")
        # export the import path so consumers/test_package get it automatically
        # (lesson: aiohttp CI failed with "No module named 'multidict'" when
        # package_info only printed PYTHONPATH instead of declaring it)
        self.runenv_info.append_path("PYTHONPATH", site)
        self.buildenv_info.append_path("PYTHONPATH", site)
        self.output.info(f"PYTHONPATH={site}")
