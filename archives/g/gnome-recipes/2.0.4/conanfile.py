#!/usr/bin/env python3
"""Conan recipe — gnome-recipes 2.0.4

HarmonyOS PC (aarch64 / OHOS) adaptation of GNOME Recipes
(https://gitlab.gnome.org/GNOME/gnome-recipes), a GTK3 recipe management
application.

OHOS adaptation summary:
  * The Todoist shopping-list export used librest (rest-0.7); the registry
    only ships librest/0.10.2, which is the rest-1.0/libsoup3 generation
    (no rest-0.7.pc, and libsoup2/libsoup3 clash in one process).  Patch
    0001 rebuilds the same form-encoded POSTs directly on libsoup 2.4 and
    drops the rest-0.7 dependency.
  * The graph is unified DOWN on the glib/2.84.0.x generation: every
    published binary of the GTK3 stack (gtk/3.24.43, atk, gdk-pixbuf,
    pango, gspell, libsoup/2.74.3-r1, ...) was built against glib/2.84.x +
    zlib/1.3.1.1, while libgoa/3.58.1, json-glib and gnome-autoar upstream
    pin glib/2.88.3 / zlib/1.3.2 — a generation in which no GTK3 binary is
    published yet.  A root override pulls those hard pins down to
    glib/2.84.0.1.1 + zlib/1.3.1.1 so the whole stack resolves from
    published binaries; libgoa is then the single node rebuilt from source
    against glib/2.84.0.1.1 on the worker (see notes.md).  The unification
    also crosses a component-naming generation gap — glib/2.88.3 renamed
    its cpp_info components to bare names (glib, gobject, gio) while 2.84.x
    spells them glib-2.0/gobject-2.0/gio-2.0 — so generate() normalizes
    consumer component references (e.g. libgoa's "glib::gio") before
    PkgConfigDeps walks the models.
  * Patches 0002/0004 skip the translation-merge and help machinery whose
    build tools (itstool, yelp-tools) do not exist on OHOS; patch 0003 makes
    the post-install script tolerable on systems without the desktop cache
    tools, and patch 0006 stops meson from executing that script at all
    (OHOS denies direct script execution; the GSettings schema compilation
    the script also drives is performed by package() instead); patch 0005
    guards the locale measurement branches behind a meson cc.links
    capability probe (HAVE__NL_MEASUREMENT_MEASUREMENT): the glibc langinfo
    item is an enum constant rather than a macro, so the probe compiles a
    reference to it; libcs without the item (e.g. OHOS) fall back to the
    metric defaults as before.
  * The OHOS filesystem denies symlink(2) outright, so a shared library
    that is source-built inside this graph (libgoa, un-pinned down to the
    unified glib) misses the unversioned linker names a Meson install would
    normally leave behind — consumers then fail with "unable to find
    library -lgoa-1.0".  generate() restores those names as real-file
    copies in the affected package folders (exactly the shape registry
    packages already take on this filesystem) before the build links.
  * gnome-autoar threads libarchive into the link, but the OHOS system
    libarchive.so.13 is a reduced build without the compression-filter
    entry points the (statically linked) autoar code relocates at
    startup.  package_info() therefore publishes the graph libarchive's
    libdir at the head of the consumer run environment's LD_LIBRARY_PATH
    so the loader keeps picking the copy the binary was linked against.
    That publication only materializes while libarchive is inside the
    consumer's run closure -- a transitive-only dep is "Skipped" by the
    graph and has no package_folder -- so the consumers must keep the
    edge visible: test_package declares libarchive/3.8.7 directly in its
    requirements() and injects the dependency libdirs into the test run
    (E669-app-consumer-run-closure-skips-transitive-so-libs).
  * The GLib tooling helpers (PkgConfigDeps glue, staged build tools,
    signing) follow the evince 48.4 recipe, with the python-tool staging
    corrected — evince never exercises gdbus-codegen, so its latent
    staged-copy flaw only surfaced here (see build approach).

Build approach (proven for Meson on this platform — see evince 48.4):
  * PkgConfigDeps emits dependency .pc files; glib's missing alias pcs
    (gio-unix-2.0, gmodule-export-2.0) are synthesized, and glib's python
    tools (glib-genmarshal, glib-mkenums, gdbus-codegen) are wrapped as
    interpreter-absolute-shebang + runpy drivers around the ORIGINAL
    package scripts (atk 2.38.0.1.1's scheme) so gdbus-codegen's in-package
    codegen-module lookup keeps working, while ELF tools (glib-compile-
    resources, glib-compile-schemas, gobject-query, gio-querymodules) are
    staged and signed for the OHOS loader.
  * MesonToolchain drives the build; libgd is an in-tree subproject of the
    release tarball, so wrap_mode=nodownload is sufficient.
"""

import glob
import os
import re
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class GnomeRecipesConan(ConanFile):
    name = "gnome-recipes"
    version = "2.0.4"
    description = "GNOME Recipes: a recipe management application for HarmonyOS PC"
    license = "GPL-3.0-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/gnome-recipes"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "gnome-recipes is supported only on Linux and OHOS"
            )

    def requirements(self):
        # GLib umbrella: unify DOWN on 2.84.0.1.1 (see module docstring).
        # The override also pulls libgoa's hard glib/2.88.3 pin back to
        # 2.84.0.1.1 (conan allows overriding a declared requirement), which
        # keeps every GTK3-stack binary usable and leaves libgoa as the only
        # source build in the graph.
        self.requires("glib/2.84.0.1.1", override=True, options={"shared": True},
                      transitive_headers=True, transitive_libs=True)
        self.requires("gtk/3.24.43", transitive_headers=True, transitive_libs=True)
        self.requires("libsoup/2.74.3-r1", transitive_headers=True, transitive_libs=True)
        self.requires("libgoa/3.58.1", transitive_headers=True, transitive_libs=True)
        self.requires("json-glib/1.10.6.1", transitive_headers=True, transitive_libs=True)
        self.requires("gnome-autoar/0.4.5", transitive_headers=True, transitive_libs=True)
        # libarchive rides in through gnome-autoar's own requirement; it is
        # declared directly so package_info() can publish its runtime libdir
        # (see the libarchive bullet in the module docstring / notes.md).
        self.requires("libarchive/3.8.7", transitive_headers=True, transitive_libs=True)
        self.requires("gspell/1.14.4", transitive_headers=True, transitive_libs=True)
        self.requires("libcanberra/0.30", transitive_headers=True, transitive_libs=True)
        # Public pkg-config closure of the glib/2.84.0.x generation, kept in
        # the host graph so PkgConfigDeps emits the .pc files referenced by
        # glib-2.0.pc / pango.pc / harfbuzz.pc / libtiff-4.pc (same pattern
        # as the activity-log 0.9.7 adaptation).
        self.requires("pcre2/10.45", transitive_headers=True, transitive_libs=True)
        self.requires("libffi/3.4.4", transitive_headers=True, transitive_libs=True)
        self.requires("graphite2/1.3.14", transitive_headers=True, transitive_libs=True)
        self.requires("xz/5.6.2", transitive_headers=True, transitive_libs=True)
        # zlib: unify down on 1.3.1.1 — the gtk3-stack binaries (libpng,
        # libtiff, pango, ...) were all published against 1.3.1.1; the 1.3.2
        # world would orphan every published binary (see notes.md).
        self.requires("zlib/1.3.1.1", override=True,
                      transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        self._ensure_tmpdir()
        self._normalize_glib_component_refs()
        self._materialize_dep_sonames()
        PkgConfigDeps(self).generate()
        self._augment_glib_pkg_config()
        self._patch_glib_pkg_config_variables()
        self._create_glib_pkg_config_aliases()
        self._patch_gio_pkg_config_variables()
        tc = MesonToolchain(self)
        tc.project_options["wrap_mode"] = "nodownload"
        tc.generate()
        self._inject_ar_ranlib()

    def build(self):
        self._ensure_tmpdir()
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        Meson(self).install()
        if self.settings.os == "OHOS":
            self._compile_schemas()
            self._sign_binaries()
            self._sign_shared_libs()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
        if self.settings.os == "OHOS":
            # The link closure binds the shared libarchive of this graph
            # (gnome-autoar is static, but its compression-filter calls are
            # relocated against libarchive.so.13), while the OHOS system
            # copy of that soname is a reduced build without the
            # compression-filter entry points -- a plain run dies with
            # "archive_write_add_filter_*: symbol not found".  The derived
            # run environment does not carry libarchive's libdir, so
            # publish it explicitly (highest priority) for consumers.
            # NOTE: this fires only while libarchive is inside the run
            # closure; a Skipped (transitive-only) dep has package_folder
            # None and the guard below stays silent -- consumers must
            # declare the edge explicitly (see the docstring bullet and
            # E669-app-consumer-run-closure-skips-transitive-so-libs).
            libarchive = self.dependencies["libarchive"]
            if libarchive.package_folder:
                for subdir in libarchive.cpp_info.libdirs or ["lib"]:
                    self.runenv_info.prepend_path(
                        "LD_LIBRARY_PATH",
                        os.path.join(libarchive.package_folder, subdir),
                    )

    def _inject_ar_ranlib(self):
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        ar = compiler_executables.get("ar")
        ranlib = compiler_executables.get("ranlib")
        if not ar:
            cc = compiler_executables.get("c") or ""
            bindir = os.path.dirname(cc) if os.sep in cc else ""
            if bindir:
                candidate = os.path.join(bindir, "llvm-ar")
                if os.path.isfile(candidate):
                    ar = candidate
                    ranlib_candidate = os.path.join(bindir, "llvm-ranlib")
                    if os.path.isfile(ranlib_candidate):
                        ranlib = ranlib_candidate
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if ar and os.path.isfile(native_file):
            with open(native_file, encoding="utf-8") as handle:
                content = handle.read()
            if "\nar =" not in content and "[binaries]" in content:
                insertion = "[binaries]\nar = '{}'\n".format(ar)
                if ranlib:
                    insertion += "ranlib = '{}'\n".format(ranlib)
                content = content.replace("[binaries]\n", insertion, 1)
                with open(native_file, "w", encoding="utf-8") as handle:
                    handle.write(content)

    def _ensure_tmpdir(self):
        tmpdir = os.path.join(self.build_folder, ".tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir

    def _normalize_glib_component_refs(self):
        # The registry carries two generations of glib adapter recipes with
        # incompatible component spellings: glib/2.84.x uses the suffixed
        # names (glib-2.0, gobject-2.0, gio-2.0, gmodule-2.0, gthread-2.0)
        # while glib/2.88.3 renamed them to the bare ones (glib, gobject,
        # gio, ...).  Consumers written against the 2.88 generation
        # (libgoa/3.58.1: cpp_info.requires = ["glib::glib", "glib::gio"])
        # make PkgConfigDeps abort with "Component 'glib::gio' not found in
        # 'glib' package requirement" once glib is unified down to 2.84.
        # Rewrite those references in-memory (both directions) before the
        # generator walks the cpp_info models — the dependency objects are
        # live in generate(), so PkgConfigDeps sees the rewritten refs.
        glib_comps = set(self.dependencies["glib"].cpp_info.components.keys())

        def fix(ref):
            pkg, _, comp = ref.partition("::")
            if pkg == "glib" and comp and comp not in glib_comps:
                if comp + "-2.0" in glib_comps:
                    return "glib::" + comp + "-2.0"
                if comp.endswith("-2.0") and comp[:-len("-2.0")] in glib_comps:
                    return "glib::" + comp[:-len("-2.0")]
            return ref

        for dep in self.dependencies.values():
            cio = dep.cpp_info
            if cio.requires:
                cio.requires = [fix(r) for r in cio.requires]
            for comp in cio.components.values():
                if comp.requires:
                    comp.requires = [fix(r) for r in comp.requires]

    def _materialize_dep_sonames(self):
        # A Meson-installed shared library normally lands as one real file
        # (libfoo.so.1.2.3) plus symlink names (libfoo.so.1, libfoo.so), and
        # the linker resolves -lfoo only through the unversioned name.  The
        # OHOS filesystem denies symlink(2) (EPERM), so a dependency node
        # source-built in this graph (libgoa, un-pinned down to the
        # glib/2.84 generation) carries ONLY the versioned real file and
        # `ld.lld -L<...>/lib -lgoa-1.0` fails with "unable to find library
        # -lgoa-1.0".  Registry-built packages show no problem on the same
        # filesystem (their symlink archive entries were materialized as
        # copies at extraction time), so restore the missing names in that
        # same copy shape; packages that already carry the names are left
        # untouched (idempotent, no-op on hosts with working symlinks).
        if self.settings.os != "OHOS":
            return
        pattern = re.compile(r"^(lib[^/]+\.so)\.(\d+(?:\.\d+)*)$")
        for dep in self.dependencies.host.values():
            package_folder = dep.package_folder
            if not package_folder:
                continue
            # A componentized dependency can leave the root cpp_info.libdirs
            # empty while its libraries still sit in the default lib/
            # layout; fall back to it, as package_info() does for libarchive.
            for subdir in dep.cpp_info.libdirs or ["lib"]:
                libdir = os.path.join(package_folder, subdir)
                if not os.path.isdir(libdir):
                    continue
                for entry in os.listdir(libdir):
                    if entry.startswith("."):
                        continue
                    full = os.path.join(libdir, entry)
                    if not os.path.isfile(full):
                        continue
                    match = pattern.match(entry)
                    if not match:
                        continue
                    base = match.group(1)
                    major = match.group(2).split(".")[0]
                    for name in (base + "." + major, base):
                        target = os.path.join(libdir, name)
                        if os.path.lexists(target):
                            continue
                        shutil.copy2(full, target)
                        self.output.info(
                            "materialized soname name from {}: {}".format(
                                entry, target
                            )
                        )

    def _augment_glib_pkg_config(self):
        # glib.so NEEDED libintl.so.8，PkgConfigDeps 生成的 Libs 缺 -lintl，
        # OHOS lld 用 --no-allow-shlib-undefined 严格校验，链接时会报
        # g_libintl_* 未定义（libayatana-indicator / evince 同款处理）。
        for pc_name in ("glib-2.0.pc", "gio-2.0.pc", "gobject-2.0.pc",
                        "gmodule-2.0.pc", "gthread-2.0.pc"):
            pc = os.path.join(self.generators_folder, pc_name)
            if not os.path.isfile(pc):
                continue
            lines = []
            for line in open(pc, encoding="utf-8").read().splitlines(keepends=True):
                if line.startswith("Libs:") and "-lintl" not in line.split():
                    line = line.rstrip("\r\n") + " -lintl\n"
                lines.append(line)
            open(pc, "w", encoding="utf-8", newline="\n").write("".join(lines))

    def _create_glib_pkg_config_aliases(self):
        # gnome-recipes 顶层 meson.build 依赖 gio-unix-2.0 与
        # gmodule-export-2.0；glib 配方只导出 glib-2.0/gobject-2.0/
        # gmodule-2.0/gthread-2.0/gio-2.0 组件。缺失的别名 .pc 由最接近的
        # 组件 .pc 合成（退回 glib-2.0.pc），只补缺不覆盖。
        glib_pc = os.path.join(self.generators_folder, "glib-2.0.pc")
        if not os.path.isfile(glib_pc):
            return
        with open(glib_pc, encoding="utf-8") as source:
            glib_content = source.read()
        aliases = {
            "gio-2.0.pc": ("gio-2.0", "glib-2.0.pc"),
            "gobject-2.0.pc": ("gobject-2.0", "glib-2.0.pc"),
            "gmodule-2.0.pc": ("gmodule-2.0", "glib-2.0.pc"),
            "gthread-2.0.pc": ("gthread-2.0", "glib-2.0.pc"),
            "gio-unix-2.0.pc": ("gio-unix-2.0", "gio-2.0.pc"),
            "gmodule-export-2.0.pc": ("gmodule-export-2.0", "gmodule-2.0.pc"),
        }
        for filename, (name, source_name) in aliases.items():
            alias_path = os.path.join(self.generators_folder, filename)
            # PkgConfigDeps already emits the per-component .pc when the glib
            # recipe declares that component; only synthesize when absent.
            if os.path.isfile(alias_path):
                continue
            source_path = os.path.join(self.generators_folder, source_name)
            if os.path.isfile(source_path):
                with open(source_path, encoding="utf-8") as handle:
                    content = handle.read()
            else:
                content = glib_content
            alias = re.sub(r"^Name:.*$", f"Name: {name}", content, flags=re.M)
            with open(alias_path, "w", encoding="utf-8") as target:
                target.write(alias)

    def _patch_glib_pkg_config_variables(self):
        glib_pc = os.path.join(self.generators_folder, "glib-2.0.pc")
        if not os.path.isfile(glib_pc):
            return
        variables = {
            "glib_genmarshal": self._stage_glib_tool("glib-genmarshal"),
            "gobject_query": self._stage_glib_tool("gobject-query"),
            "glib_mkenums": self._stage_glib_tool("glib-mkenums"),
        }
        with open(glib_pc, encoding="utf-8") as source:
            content = source.read()
        for variable, value in variables.items():
            if re.search(rf"^{re.escape(variable)}=", content, flags=re.M):
                content = re.sub(
                    rf"^{re.escape(variable)}=.*$",
                    f"{variable}={value}",
                    content,
                    flags=re.M,
                )
            else:
                content = f"{variable}={value}\n" + content
        with open(glib_pc, "w", encoding="utf-8") as target:
            target.write(content)

    def _patch_gio_pkg_config_variables(self):
        gio_pc = os.path.join(self.generators_folder, "gio-2.0.pc")
        if not os.path.isfile(gio_pc):
            return
        variables = {
            "gio": self._stage_glib_tool("gio"),
            "gio_querymodules": self._stage_glib_tool("gio-querymodules"),
            "glib_compile_schemas": self._stage_glib_tool("glib-compile-schemas"),
            "glib_compile_resources": self._stage_glib_tool("glib-compile-resources"),
            "gdbus": self._stage_glib_tool("gdbus"),
            "gdbus_codegen": self._stage_glib_tool("gdbus-codegen"),
            "gresource": self._stage_glib_tool("gresource"),
            "gsettings": self._stage_glib_tool("gsettings"),
        }
        with open(gio_pc, encoding="utf-8") as source:
            content = source.read()
        for variable, value in variables.items():
            if re.search(rf"^{re.escape(variable)}=", content, flags=re.M):
                content = re.sub(
                    rf"^{re.escape(variable)}=.*$",
                    f"{variable}={value}",
                    content,
                    flags=re.M,
                )
            else:
                content = f"{variable}={value}\n" + content
        with open(gio_pc, "w", encoding="utf-8") as target:
            target.write(content)

    def _stage_glib_tool(self, name):
        source = os.path.join(self.dependencies["glib"].package_folder, "bin", name)
        tools_dir = os.path.join(self.build_folder, ".glib-tools")
        os.makedirs(tools_dir, exist_ok=True)
        target = os.path.join(tools_dir, name)
        if not os.path.isfile(source):
            return target
        with open(source, "rb") as handle:
            first_line = handle.readline(128)
        if b"python" in first_line and self.settings.os == "OHOS":
            # Python 脚本工具（glib-genmarshal/glib-mkenums/gdbus-codegen
            # 等）：不拷贝原文件，改写"解释器绝对路径 shebang + runpy 执行原
            # 包脚本"的 wrapper。runpy 执行时 __file__ 仍指向包内原脚本，
            # gdbus-codegen 自带的引导逻辑（按 __file__ 的上级目录找
            # share/glib-2.0/codegen）才能命中随包 codegen 模块；直接拷贝
            # 进 .glib-tools/ 会让它去 <build>/codegen 找而报
            # ModuleNotFoundError（真机实测）。wrapper 形态与平台内
            # atk/2.38.0.1.1 的 _create_python_tool_wrapper 一致。
            return self._write_python_tool_wrapper(target, source)
        if not os.path.isfile(target):
            shutil.copy2(source, target)
            os.chmod(target, 0o755)
        if self.settings.os == "OHOS":
            self._make_elf_tool_runnable(target)
        return target

    def _write_python_tool_wrapper(self, wrapper, script):
        # shebang 用解释器绝对路径（realpath）：真机上 /bin/sh、/usr/bin/env
        # 这类系统解释器作为 shebang 不可 exec，而包内 python 解释器可以；
        # 该 "#!{解释器} + runpy 原脚本" 形态与 atk/2.38.0.1.1 的
        # _create_python_tool_wrapper 相同（平台内已 CI 验证）。
        python = os.path.realpath(sys.executable)
        with open(wrapper, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(
                f"#!{python}\n"
                "import runpy\n"
                "import sys\n"
                f"sys.argv = [{script!r}] + sys.argv[1:]\n"
                f"runpy.run_path({script!r}, run_name='__main__')\n"
            )
        os.chmod(wrapper, 0o755)
        return wrapper

    def _make_elf_tool_runnable(self, tool):
        # OHOS 要求 ELF 带 .codesign 段才能 exec（未签名报 Operation not
        # permitted）；glib 包内工具未签名。顺序关键：先 patchelf 注入
        # runpath（指向 glib libdir 以加载 libgio-2.0.so.0 等），再签名——
        # 签名后再改 ELF 会破坏 .codesign，exec 仍报 Operation not permitted。
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        glib_libdir = os.path.join(self.dependencies["glib"].package_folder, "lib")
        self.run('patchelf --set-rpath "{r}" "{f}"'.format(r=glib_libdir, f=tool))
        if os.path.isfile(objcopy) and os.path.isfile(signer):
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(
                oc=objcopy, f=tool
            ))
            signed = tool + ".signed"
            self.run('{sg} sign -inFile "{f}" -outFile "{o}" -selfSign 1'.format(
                sg=signer, f=tool, o=signed
            ))
            if os.path.isfile(signed):
                os.replace(signed, tool)
        os.chmod(tool, 0o755)

    def _compile_schemas(self):
        # The post-install script can only call glib-compile-schemas when it
        # is on PATH; guarantee the compiled schema by running the staged,
        # signed tool against the package folder directly (idempotent).
        schema_dir = os.path.join(self.package_folder, "share", "glib-2.0", "schemas")
        tool = os.path.join(self.build_folder, ".glib-tools", "glib-compile-schemas")
        if os.path.isdir(schema_dir) and os.path.isfile(tool):
            self.run('"{tool}" "{schema_dir}"'.format(tool=tool, schema_dir=schema_dir))

    def _sign_binaries(self):
        bindir = os.path.join(self.package_folder, "bin")
        binaries = sorted(
            os.path.join(bindir, name)
            for name in os.listdir(bindir)
            if os.path.isfile(os.path.join(bindir, name))
        ) if os.path.isdir(bindir) else []
        if not binaries:
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for tool in (objcopy, signer):
            if not os.path.isfile(tool):
                raise FileNotFoundError(f"Required OHOS signing tool is missing: {tool}")
        for binary in binaries:
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(
                oc=objcopy, f=binary
            ))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(
                sg=signer, f=binary
            ))

    def _sign_shared_libs(self):
        libdir = os.path.join(self.package_folder, "lib")
        shared_objects = glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        shared_objects += glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        if not shared_objects:
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for tool in (objcopy, signer):
            if not os.path.isfile(tool):
                raise FileNotFoundError(f"Required OHOS signing tool is missing: {tool}")
        for shared_object in shared_objects:
            if os.path.islink(shared_object):
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(
                oc=objcopy, f=shared_object
            ))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(
                sg=signer, f=shared_object
            ))
