#!/usr/bin/env python3
"""Conan recipe for PDL 2.104 (Perl Data Language) - Perl + XS(C) core.

Upstream: CPAN PDLPorters/pdl (release PDL-2.104 by ETJ). Platform task id=9406.

Two environment facts verified before writing this recipe:

  1. The CI worker IS an OHOS machine (its logs run /data/service/hnp/bin/ruby
     directly), so the ohpcd-published OHOS/armv8 perl/5.42.2.3 can execute
     there and an XS build is possible at all.
  2. OHOS rejects XS ELF modules that entered the Conan package cache before
     being signed, so every .so must be signed in the BUILD TREE with
     /data/service/hnp/bin/binary-sign-tool (same approach as the perl recipe).

Dependency strategy (route A, same shape as the jekyll gem closure): PDL needs
four CPAN modules that are not published on ohpcd (Devel::CheckLib, File::Map,
Test::Deep, Test::Warn). They are pinned by url+sha256 in conandata.yml, built
into a private stage, and shipped inside this package, so one PR settles PDL
instead of four extra PRs for tiny modules. Two other deps are already
published (perl-file-which, perl-test-exception) and are ordinary requires.
  3. ExtUtils::CBuilder 的编译器探测会被 perl 的 Config 坑到：OHOS 上 perl 的
     Config.pm 里 cc 被写成 "/bin/sh /data/service/hnp/bin/clang"（perl Configure 的
     -Dcc 形式）。CBuilder::have_compiler 会 split_like_shell 后直接执行，于是变成
     "sh <ELF>" -> 试编译失败 -> Module::Build 报 no compiler detected to compile
     lib/File/Map.c。CBuilder/Base.pm:40 明确认 $ENV{CC}，因此本配方把 CC/LD
     规范化成单个真实存在的编译器路径后再传给子进程。
  4. PERL5LIB 只能放**真正的模块根**（lib/perl5、版本目录、含 '-' 的 archname 目录、
     site_perl/<ver>[/<arch>]）。perl 包里存在 <ver>/encoding/warnings.pm：一旦把
     <ver>/encoding 这类一级子目录放进 @INC，require warnings 就会命中它，核心 warnings
     包随即失效，表现为 Undefined subroutine &warnings::register_categories 或 vars.pm
     BEGIN 失败（CI 实测，且与 Test::Warnings 无关，是 @INC 构造问题）。
  5. 本仓 perl 包不可重定位：Config.pm 里 archlibexp 等被 Configure 写死为 /lib/perl5/...，
     实际文件在 <perl包>/lib/perl5/...。MakeMaker 会直接 opendir 该路径而硬失败，故把修正过
     路径的 Config.pm/Config_heavy.pl 放进 stage（PERL5LIB 优先于内置路径），XS 头文件再用
     CPATH 指向真实 CORE 目录兜底。
     （注：CI 的 PATH 不含 /data/service/hnp/bin，所以只能走绝对路径。）
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy,
                                export_conandata_patches, get)
from conan.tools.layout import basic_layout

_TARBALL = "PDL-2.104.tar.gz"
_VENDORED = [
    # 顺序即依赖顺序：
    #   Module::Build 最先——File::Map 是 Module::Build 发行版；
    #   Sub::Exporter::Progressive 是 File::Map 的 runtime 依赖（纯 Perl，直接拷 lib/）；
    #   File::Map 的 test 期前置已由补丁 0001 从它的 META 里去掉（见 conandata）。
    "Module-Build-0.4234.tar.gz",
    "Sub-Exporter-Progressive-0.001013.tar.gz",
    "Devel-CheckLib-1.16.tar.gz",
    "File-Map-0.71.tar.gz",
    "Test-Deep-1.205.tar.gz",
    "Test-Warn-0.37.tar.gz",
]
_PERL = "perl/5.42.2.3"
_SIGN_TOOL = "/data/service/hnp/bin/binary-sign-tool"
_OBJCOPY = "/data/service/hnp/bin/llvm-objcopy"

# Upstream suite is 82 t/*.t files; CI has a 3600 s per-package budget and the
# whole closure must be built first, so a declared, honest subset is run.
_TEST_SUBSET = [
    "t/core.t",
    "t/basic.t",
    "t/slice.t",
    "t/matrixops.t",
    "t/reduce.t",
    "t/ufunc.t",
]


class PdlConan(ConanFile):
    name = "pdl"
    version = "2.104"
    description = "Perl Data Language 2.104 - array/numerical processing for Perl (XS core)"
    license = "Artistic-1.0-Perl OR GPL-1.0-or-later"
    homepage = "https://metacpan.org/dist/PDL"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # Interpreter plus the two already-published pure-Perl dependencies.
        self.requires(_PERL)
        self.requires("perl-file-which/1.27")
        self.requires("perl-test-exception/0.43")
        # PDL 的测试套件需要（ohpcd 已发布，CI 日志里出现过该包）
        self.requires("perl-sub-uplevel/0.2800")

    def source(self):
        get(self, **self.conan_data["sources"][_TARBALL], strip_root=True)
        for name in _VENDORED:
            dist = name[: -len(".tar.gz")]
            get(self, **self.conan_data["sources"][name],
                destination=os.path.join(self.source_folder, "_vendor", dist),
                strip_root=True)
        apply_conandata_patches(self)

    # ------------------------------------------------------------------ helpers
    def _perl(self):
        return os.path.join(self.dependencies["perl"].package_folder, "bin", "perl")

    def _perl5_roots(self):
        """只收集**真正的模块根**目录，供 PERL5LIB 使用。

        why：绝不能把模块目录下的一级子目录都当模块根。perl 包里存在
        <ver>/encoding/warnings.pm，一旦把 <ver>/encoding 放进 @INC，
        require warnings 就会命中它，核心 warnings 包随即失效
        （CI 实测：Undefined subroutine &warnings::register_categories、
        vars.pm BEGIN 失败）。因此这里只放：lib/perl5 本身、版本目录、
        形如 arch 的子目录（含 '-'，如 aarch64-linux-thread-multi）、
        以及 site_perl/<ver>[/<arch>]。
        """
        roots = []
        try:
            items = list(self.dependencies.items())
        except Exception:
            items = []
        for _name, dep in items:
            folder = getattr(dep, 'package_folder', None)
            if not folder:
                continue
            base = os.path.join(folder, 'lib', 'perl5')
            if not os.path.isdir(base):
                continue
            roots.append(base)
            for a in sorted(os.listdir(base)):
                sub = os.path.join(base, a)
                if not os.path.isdir(sub):
                    continue
                if a.startswith('5.'):  # 版本目录，如 5.42.2
                    roots.append(sub)
                    for b in sorted(os.listdir(sub)):
                        sub2 = os.path.join(sub, b)
                        if os.path.isdir(sub2) and '-' in b:
                            roots.append(sub2)
                elif a == 'site_perl':
                    roots.append(sub)
                    for v in sorted(os.listdir(sub)):
                        vd = os.path.join(sub, v)
                        if not os.path.isdir(vd):
                            continue
                        roots.append(vd)
                        for b in sorted(os.listdir(vd)):
                            sub2 = os.path.join(vd, b)
                            if os.path.isdir(sub2) and '-' in b:
                                roots.append(sub2)
        seen, out = set(), []
        for p in roots:
            if p not in seen:
                seen.add(p)
                out.append(p)
        return out

    def _relocate_perl_config(self, stage):
        """把 perl 包里路径写死的 Config.pm / Config_heavy.pl 复制进 stage 并修正前缀。

        why：本仓的 perl 包不可重定位——Configure 用了 -Dprefix=/，于是 Config 里
        archlibexp/privlibexp 等被写死成 /lib/perl5/...，而文件实际在 <perl 包>/lib/perl5/...
        CBuilder 靠 -I 编译（CPATH 可兜），但 ExtUtils::MakeMaker 会直接
        opendir('/lib/perl5/.../CORE') 找头文件并硬失败（CI 实测：Failed to opendir ...）。
        PERL5LIB 中的路径优先于 perl 内置路径，因此把修正过的 Config 放进 stage 即可；
        不改 perl 包本身。
        """
        import glob as _glob
        perl_root = os.path.dirname(os.path.dirname(self._perl()))
        archdirs = [d for d in _glob.glob(os.path.join(perl_root, 'lib', 'perl5', '*', '*'))
                    if os.path.isfile(os.path.join(d, 'Config_heavy.pl'))]
        if not archdirs:
            self.output.warning('[pdl] no perl Config dir found; XS/MM builds may fail')
            return
        src = archdirs[0]
        rel = os.path.relpath(src, os.path.join(perl_root, 'lib', 'perl5'))
        dst = os.path.join(stage, 'lib', 'perl5', rel)
        os.makedirs(dst, exist_ok=True)
        for name in ('Config.pm', 'Config_heavy.pl'):
            path = os.path.join(src, name)
            if not os.path.isfile(path):
                continue
            text = open(path, encoding='utf-8', errors='replace').read()
            text = text.replace('/lib/perl5', perl_root + '/lib/perl5')
            text = text.replace("prefix='/';", "prefix='" + perl_root + "';")
            with open(os.path.join(dst, name), 'w', encoding='utf-8') as fh:
                fh.write(text)
            self.output.warning('[pdl] relocated ' + name + ' -> ' + dst)

    def _perl_core_dirs(self):
        """返回 perl 包里真实的 CORE 目录（放 EXTERN.h 等 XS 头文件的地方）。

        why：本仓的 perl 包不可重定位——它的 Config.pm 里 archlibexp 被 Configure 写死成
        /lib/perl5/5.42.2/<archname>（CI 日志里 CBuilder 给出的正是
        -I/lib/perl5/5.42.2/aarch64-linux-thread-multi/CORE），而文件实际在
        <perl 包>/lib/perl5/... 之下，于是 XS 编译报 EXTERN.h file not found。
        把真实 CORE 目录塞进 CPATH 即可让编译器找到头文件，既不改 perl 包，也不依赖它的坏路径。
        """
        import glob as _glob
        perl_root = os.path.dirname(os.path.dirname(self._perl()))
        return sorted(_glob.glob(os.path.join(perl_root, "lib", "perl5", "*", "*", "CORE")))

    def _cc(self):
        """返回**单个、可执行、不含 shell 前缀**的编译器路径。

        why：OHOS 上 perl 的 Config.pm 里 cc 被写成 "/bin/sh /data/service/hnp/bin/clang"
        （perl Configure 的 -Dcc 形式）。ExtUtils::CBuilder 会按 shell 拆分后直接执行，
        于是变成 "sh <ELF>" → 试编译失败 → have_compiler 返回 0 →
        Module::Build 报 "no compiler detected to compile 'lib/File/Map.c'"。
        CBuilder::Base.pm:40 明确认 $ENV{CC}，所以这里规范化后显式传给子进程即可绕过。
        """
        conf = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cands = []
        for key in ("c", "cpp"):
            if conf.get(key):
                cands.append(conf[key])
        for env in ("CC", "CXX"):
            if os.environ.get(env):
                cands.append(os.environ[env])
        for cand in ("clang", "cc"):
            for base in ("/data/service/hnp/bin", "/usr/bin", "/usr/local/bin"):
                cands.append(os.path.join(base, cand))
        for cand in cands:
            tokens = str(cand).split()
            if not tokens:
                continue
            path = tokens[-1]
            if os.path.isfile(path):
                return path
        return None

    def _env(self, perl5_extra, cc):
        env = dict(os.environ)
        # INSTALL_BASE 的语义：模块落在 <base>/lib/perl5 之下（CI 实测日志可见
        # ".../stage/lib/perl5/Module/Build/..."）。因此 PERL5LIB 必须把
        # <base>/lib/perl5 及其 archname 子目录一并放进去，否则 Build.PL 找不到
        # 刚刚装进 stage 的 Module::Build（首轮 CI 就是栽在这里）。
        expanded = []
        for base in perl5_extra:
            expanded.append(base)
            sub = os.path.join(base, "lib", "perl5")
            if os.path.isdir(sub):
                expanded.append(sub)
                for name in sorted(os.listdir(sub)):
                    cand = os.path.join(sub, name)
                    if os.path.isdir(cand):
                        expanded.append(cand)
        env["PERL5LIB"] = os.pathsep.join(expanded + self._perl5_roots())
        env["PERL_MM_USE_DEFAULT"] = "1"
        env["PERL_MM_NONINTERACTIVE"] = "1"
        # Keep the build offline: PDL's Makefile.PL probes optional deps and
        # must never try to fetch anything.
        env["PERL_AUTOINSTALL"] = "--skipdeps"
        if cc:
            # 同时给 CBuilder 用的 CC/LD 一个干净路径（见 _cc 的说明）
            env["CC"] = cc
            env["LD"] = cc
        # PDL 默认会探测并链接 -lpthread 并定义 PDL_PTHREAD，其代码随即引用
        # pthread_setcanceltype —— 而 OHOS 的 libc 不导出该符号（仓内 sysroot 的
        # libpthread.a 是空占位，导致探测"通过"但运行时加载失败：CI 实测
        # "Error relocating Core.so: pthread_setcanceltype: symbol not found"）。
        # PDL 的 Makefile.PL 支持 POSIX_THREADS_LIBS 开关，置空即按上游提示
        # "PDL will be built without POSIX thread support" 构建。
        env["POSIX_THREADS_LIBS"] = ""
        cores = self._perl_core_dirs()
        if cores:
            # 让编译器无论如何都能找到 perl 的 XS 头文件（见 _perl_core_dirs 的说明）
            env["CPATH"] = os.pathsep.join(cores)
            self.output.warning("[pdl] CPATH=" + env["CPATH"])
        return env

    def _run(self, cmd, cwd, env, what):
        proc = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True)
        out = (proc.stdout or b"").decode(errors="replace")
        err = (proc.stderr or b"").decode(errors="replace")
        tail = "\n".join((out.splitlines() + err.splitlines())[-30:])
        self.output.info("[" + what + "] " + " ".join(cmd) + " rc=" + str(proc.returncode) + "\n" + tail)
        if proc.returncode != 0:
            raise ConanInvalidConfiguration(
                what + " failed (rc=" + str(proc.returncode) + "):\n" + tail)
        return proc

    # 纯 Perl、且 Makefile.PL 在本环境不可用的发行版（Dist::Zilla 生成的
    # Makefile.PL 会在加载 ExtUtils::MakeMaker 时撞上核心 warnings 版本错配：
    # "Undefined subroutine &warnings::register_categories"）。
    # 这类模块按本仓既有范式直接拷 lib/ 到 site-lib，不做编译（同 perl-file-which）。
    _PURE_PERL = ("Sub-Exporter-Progressive-0.001013.tar.gz",)

    def _install_pure_perl(self, tree, stage):
        src = os.path.join(tree, "lib")
        dst = os.path.join(stage, "lib", "perl5")
        if not os.path.isdir(src):
            raise ConanInvalidConfiguration("pure-Perl dist has no lib/: " + tree)
        os.makedirs(dst, exist_ok=True)
        shutil.copytree(src, dst, dirs_exist_ok=True)
        copied = sum(len(f) for _, _, f in os.walk(src))
        self.output.warning("[pdl] pure-Perl install " + os.path.basename(tree)
                            + ": " + str(copied) + " files -> " + dst)

    def _install_base(self, pl_args):
        for arg in pl_args:
            if arg.startswith("INSTALL_BASE="):
                return arg.split("=", 1)[1]
        return os.path.join(self.build_folder, "stage")

    def _perl_make(self, perl, tree, pl_args, perl5_extra, cc, do_install=True):
        env = self._env(perl5_extra, cc)
        # 把工作目录与顶层文件打进日志：首轮 CI 就是栽在"某棵树没有 Makefile.PL"
        # 上，当时只能靠猜（真因是 File-Map 是 Module::Build 发行版）。
        top = sorted(os.listdir(tree)) if os.path.isdir(tree) else []
        self.output.warning("[pdl] cwd=" + tree + " top-level=" + ", ".join(top[:12]))
        if not os.path.isfile(os.path.join(tree, "Makefile.PL")) and \
                os.path.isfile(os.path.join(tree, "Build.PL")):
            # Module::Build 发行版（例如 File::Map 0.71）：Build.PL + Build install
            self._run([perl, "Build.PL", "--install_base", self._install_base(pl_args)],
                      tree, env, "Build.PL")
            self._run([perl, "Build"], tree, env, "Build")
            if do_install:
                self._run([perl, "Build", "install"], tree, env, "Build install")
            return env
        self._run([perl, "Makefile.PL"] + pl_args, tree, env, "Makefile.PL")
        self._run(["make"], tree, env, "make")
        if do_install:
            self._run(["make", "install"], tree, env, "make install")
        return env

    def _sign_tree(self, search_root):
        backslash = 'OHOS rejects unsigned XS: sign in the build tree before install'
        if str(self.settings.os) != 'OHOS':
            return
        sign_tool = _SIGN_TOOL
        objcopy = _OBJCOPY
        if not (os.path.isfile(sign_tool) and os.path.isfile(objcopy)):
            raise ConanInvalidConfiguration(
                'OHOS signing tools not found: ' + sign_tool + ' / ' + objcopy)
        failures = []
        signed = 0
        for root, _dirs, files in os.walk(search_root):
            for filename in files:
                if not filename.endswith('.so'):
                    continue
                path = os.path.join(root, filename)
                try:
                    with open(path, 'rb') as handle:
                        if handle.read(4) != bytes([0x7f]) + b'ELF':
                            continue
                except OSError:
                    continue
                tmp_signed = path + '.signed'
                try:
                    if os.path.exists(tmp_signed):
                        os.remove(tmp_signed)
                    rr = subprocess.run([objcopy, '--remove-section', '.codesign', path],
                                        check=False, capture_output=True, text=True)
                    ro = (rr.stdout + rr.stderr).strip()
                    if rr.returncode != 0 and not ('.codesign' in ro and 'not found' in ro.lower()):
                        failures.append(path + ': objcopy: ' + (ro or str(rr.returncode)))
                        continue
                    sr = subprocess.run([sign_tool, 'sign', '-inFile', path, '-outFile', tmp_signed,
                                         '-selfSign', '1'], check=False, capture_output=True, text=True)
                    if sr.returncode != 0 or not os.path.exists(tmp_signed):
                        so = (sr.stdout + sr.stderr).strip()
                        failures.append(path + ': sign: ' + (so or str(sr.returncode)))
                        continue
                    os.replace(tmp_signed, path)
                    os.chmod(path, 0o755)
                    signed += 1
                finally:
                    if os.path.exists(tmp_signed):
                        try:
                            os.remove(tmp_signed)
                        except OSError:
                            pass
        self.output.warning('[pdl] signed ' + str(signed) + ' XS objects under ' + search_root)
        if failures:
            for f in failures[:5]:
                self.output.warning('[pdl] sign failure: ' + f[:200])
            raise ConanInvalidConfiguration('failed to sign ' + str(len(failures)) + ' ELF artifacts')

    def _run_tests(self, perl, tree, env):
        present = [f for f in _TEST_SUBSET if os.path.isfile(os.path.join(tree, f))]
        missing = [f for f in _TEST_SUBSET if f not in present]
        if missing:
            self.output.warning("test files not found (skipped): " + ", ".join(missing))
        if not present:
            self.output.warning("no upstream test files found; nothing run")
            return
        # 测试需要 PDL 自己构建的模块：blib/lib（纯 Perl，含 Test::PDL）与
        # blib/arch（XS），以及源码树的 lib/。
        test_env = dict(env)
        extra = [os.path.join(tree, "blib", "lib"), os.path.join(tree, "blib", "arch"),
                 os.path.join(tree, "lib")]
        existing = test_env.get("PERL5LIB", "")
        test_env["PERL5LIB"] = os.pathsep.join(
            [p for p in extra if os.path.isdir(p)] + ([existing] if existing else []))
        self.output.warning("[pdl] test PERL5LIB=" + test_env["PERL5LIB"][:400])
        self._run([perl, "-MTest::Harness", "-e", "runtests @ARGV", "--"] + present,
                  tree, test_env, "prove-subset")

    # ------------------------------------------------------------------ pipeline
    def build(self):
        cc = self._cc()
        perl = self._perl()
        if not os.path.isfile(perl):
            raise ConanInvalidConfiguration("perl executable not found: " + perl)
        if not cc:
            raise ConanInvalidConfiguration("no C compiler found for the XS core")

        # 1) vendored deps -> private stage, installed inside the package later
        stage = os.path.join(self.build_folder, "stage")
        os.makedirs(stage, exist_ok=True)
        # 先做 perl 重定位：MakeMaker/CBuilder 都依赖正确的 Config 路径
        self._relocate_perl_config(stage)
        for name in _VENDORED:
            dist = name[: -len(".tar.gz")]
            tree = os.path.join(self.source_folder, "_vendor", dist)
            if name in self._PURE_PERL:
                self._install_pure_perl(tree, stage)
                continue
            self._perl_make(perl, tree, ["INSTALL_BASE=" + stage], [stage], cc)

        # 2) PDL itself: build in tree, sign, test, then install into the stage
        pdl_stage = os.path.join(self.build_folder, "stage_pdl")
        os.makedirs(pdl_stage, exist_ok=True)
        env = self._perl_make(perl, self.source_folder,
                              ["INSTALL_BASE=" + pdl_stage], [stage], cc, do_install=False)
        self._sign_tree(self.source_folder)
        self._run_tests(perl, self.source_folder, env)
        self._run(["make", "install"], self.source_folder, env, "make install")

    def package(self):
        for stage in ("stage", "stage_pdl"):
            src = os.path.join(self.build_folder, stage, "lib", "perl5")
            if os.path.isdir(src):
                copy(self, "*", src=src,
                     dst=os.path.join(self.package_folder, "lib", "perl5"))
        # scripts shipped by PDL (script/perldl, script/pdl, script/pdldoc)
        src = os.path.join(self.build_folder, "stage_pdl", "bin")
        if os.path.isdir(src):
            copy(self, "*", src=src, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "Artistic", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "Copying", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        bindir = os.path.join(self.package_folder, 'bin')
        if os.path.isdir(bindir):
            self.cpp_info.bindirs = ['bin']
            self.runenv_info.prepend_path('PATH', bindir)
        base = os.path.join(self.package_folder, 'lib', 'perl5')
        own = [base]
        if os.path.isdir(base):
            own += [os.path.join(base, d) for d in sorted(os.listdir(base))
                    if os.path.isdir(os.path.join(base, d))]
        # 依赖包（perl、perl-file-which、perl-test-exception、perl-sub-uplevel）的模块
        # 目录也要进消费端 PERL5LIB，否则 use PDL 时 PDL::IO::Pic 会因缺 File::Which
        # 在 BEGIN 阶段失败（CI 实测：Can't locate File/Which.pm in @INC）。
        for path in own + self._perl5_roots():
            self.runenv_info.prepend_path('PERL5LIB', path)
            self.buildenv_info.prepend_path('PERL5LIB', path)
