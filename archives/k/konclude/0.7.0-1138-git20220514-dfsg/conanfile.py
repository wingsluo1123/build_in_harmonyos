#!/usr/bin/env python3
"""Conan recipe for konclude 0.7.0-1138-git20220514-dfsg on OpenHarmony PC.

Upstream: konclude/Konclude — a parallel, tableau-based, high-performance
          reasoner for the Description Logic SROIQV(D) / OWL 2 DL.
          Source identity: commit 056334ad728429308991e135500d129b8c652490
          (2022-05-14, the development snapshot behind the Debian/Ubuntu
          version 0.7.0+1138+git20220514~dfsg).  License: LGPL-3.0.

Build system: qmake.  The upstream tree ships hand-written ``.pro`` files
(``Konclude.pro``, ``KoncludeWithoutRedland.pro``, ``KoncludeLIB.pro``) plus a
378 KB ``Konclude.pri`` that lists the 2580 ``.cpp`` / 2653 header files; there
is no CMakeLists.txt, no Autotools and no Meson, so qmake is the upstream-native
builder and no build system is re-invented here (R1 "parameter minimisation").
``qmake``/``moc``/``rcc`` and the whole Qt5 runtime are supplied by the
``qt5-qtbase`` package that this recipe requires.

OHOS adaptation is almost entirely recipe-level (R8 "source modification: four
don'ts"); exactly one upstream source line is patched, and it is a *platform
independent upstream defect* rather than an OHOS workaround:

  * ``patches/0001-null-guard-evaluation-order.patch`` (``patch_type: bugfix``) —
    in ``applyATLEASTRule()`` the author's own NULL guard for
    ``atmostConcept->getOperandList()`` sits *after* the
    ``hasIdenticalConceptOperands()`` call it protects.  C++ short-circuit
    evaluation runs the call first, so a cardinality restriction without an
    explicit operand list dereferences NULL (``SIGSEGV`` at ``0x10``) — measured
    deterministically (3/3) on ``Tests/roberts-family-full-D.owl.xml``
    classification/realization, while ``consistency``, ``galen`` and ``lubm`` are
    unaffected.  The fix only hoists that existing guard in front of the call
    (pure ``||`` operand swap; non-NULL semantics are bit-for-bit unchanged), so
    no ``__OHOS__`` guard and no behaviour change on any platform is introduced.
    Full evidence chain is recorded in ``conandata.yml`` (patch evidence block)
    and ``notes.md`` §9.3 (the PR-carried evidence; ``reports/*.md`` is a local
    working copy that is not committed, per ``.gitcode/review-memory.md`` §19 and
    the repository's ``reports/`` .gitignore rule).

  * ``qt5-qtbase``'s own ``bin/qt.conf`` and ``mkspecs/{modules,modules-inst}/*.pri``
    still point at the *build* directory of the qt5-qtbase package
    (``$HOME/.conan2/p/b/qt5-q<id>/b``), which no longer exists once the package
    has been uploaded and re-downloaded from the artifact repository.  Without a
    fix, ``qmake`` aborts with ``Project ERROR: Unknown module(s) in QT: core gui
    xml network concurrent``.  ``_fix_qtbase_paths()`` rewrites those files to
    the package folder; the identical relocatability fix is already used by
    ``archives/q/qt5-qtdeclarative/5.15.2`` for the same dependency.

  * The upstream ``Konclude.pro`` links the **x86_64 pre-built** Redland stack
    that is committed inside the tree
    (``External/librdf/Linux/x64/lib/release/{librdf,libraptor2,librasqal,libxml2}.a``)
    plus ``External/jemalloc/Linux/x64/lib/release/libjemalloc.a``.  Those
    objects are x86_64 and unusable on aarch64; and their sources are not in the
    tree, so ``raptor2``/``rasqal`` would have to be adapted and published as
    separate Conan dependencies first (R36).  Both are absent from this
    repository and from the OHOS remote — probing them against the configured
    remote answers "Unable to find ... in remotes" for
    ``raptor2/2.0.15`` and ``rasqal/0.9.33`` respectively.

    This recipe therefore uses the *upstream-provided* variant
    ``KoncludeWithoutRedland.pro``, which drops ``KONCLUDE_REDLAND_INTEGRATION``.
    Delivered and verified on the target device: OWL 2 XML / Functional-Style
    parsing, the full reasoning core (classification, consistency, class
    satisfiability, realisation), the OWLlink XML interface (file and HTTP
    server), and SPARQL query answering through Konclude's own simple parser when
    the knowledge base comes from an OWL/XML ontology (measured: the upstream
    roberts-family SPARQL query returns 331 answers).  NOT delivered: RDF non-XML
    serialisation parsing (Turtle etc.) and the Rasqal/Redland-backed complex
    SPARQL path over RDF data — loading a ``.ttl`` file silently yields an empty
    knowledge base, which is why the upstream `.ttl`-driven SPARQL invocation is
    reported as not passing rather than exempted.  Adapting ``raptor2``/``rasqal``
    remains a separate dependency task (PF4/R36).

The product is the ``Konclude`` command line application, so the package is
declared ``package_type = "application"``, installs ``bin/Konclude`` (plus the
upstream ``Configs/`` configuration files, which the documented invocations
reference with ``-c``) and the software-level ``commands.json`` is provided (R38).
"""

import os
import re
import shlex

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout


class KoncludeConan(ConanFile):
    name = "konclude"
    version = "0.7.0-1138-git20220514-dfsg"
    description = (
        "Konclude: parallel tableau-based OWL 2 DL (SROIQV(D)) reasoner — "
        "classification, consistency, satisfiability, realisation and OWLlink"
    )
    license = "LGPL-3.0"
    homepage = "https://github.com/konclude/Konclude"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qt5-qtbase/5.15.2.2")

    def validate(self):
        # R32: OHOS must be accepted explicitly, never matched by `== "Linux"`.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.name} only supports Linux and OHOS, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        source_data = self.conan_data["sources"][self.version]
        get(self, url=source_data["url"], sha256=source_data["sha256"], strip_root=True)

    @staticmethod
    def _fix_qtbase_paths(qtbase_pkg):
        """Make the qt5-qtbase package relocatable (see module docstring).

        Rewrites ``bin/qt.conf`` and every ``mkspecs/{modules,modules-inst}/*.pri``
        that still references the qt5-qtbase *build* directory so that both point
        at the package folder the consumer actually received.
        """
        qt_conf = os.path.join(qtbase_pkg, "bin", "qt.conf")
        if os.path.isfile(qt_conf):
            with open(qt_conf, "w", encoding="utf-8") as handle:
                handle.write(
                    "[EffectivePaths]\n"
                    "Prefix=..\n"
                    "[DevicePaths]\n"
                    f"Prefix={qtbase_pkg}\n"
                    "[Paths]\n"
                    f"Prefix={qtbase_pkg}\n"
                    f"HostPrefix={qtbase_pkg}\n"
                    "Sysroot=\n"
                    "SysrootifyPrefix=false\n"
                    "TargetSpec=linux-clang\n"
                    "HostSpec=linux-clang\n"
                )

        build_dir_pattern = re.compile(r"(/[^\s]*/\.conan2/p/b/qt5-q[0-9a-f]+/b)")
        rewritten = 0
        for modules_dir_name in ("modules", "modules-inst"):
            modules_dir = os.path.join(qtbase_pkg, "mkspecs", modules_dir_name)
            if not os.path.isdir(modules_dir):
                continue
            for pri_file in os.listdir(modules_dir):
                if not pri_file.endswith(".pri"):
                    continue
                pri_path = os.path.join(modules_dir, pri_file)
                with open(pri_path, "r", encoding="utf-8") as handle:
                    content = handle.read()
                fixed = build_dir_pattern.sub(qtbase_pkg, content)
                if fixed != content:
                    with open(pri_path, "w", encoding="utf-8") as handle:
                        handle.write(fixed)
                    rewritten += 1
        return rewritten

    def build(self):
        apply_conandata_patches(self)

        qtbase = self.dependencies["qt5-qtbase"]
        qtbase_pkg = qtbase.package_folder
        rewritten = self._fix_qtbase_paths(qtbase_pkg)
        self.output.info(f"qt5-qtbase relocatability fix applied ({rewritten} .pri rewritten)")

        qmake = os.path.join(qtbase_pkg, "bin", "qmake")
        if not os.path.isfile(qmake):
            raise ConanException(
                f"qt5-qtbase/{qtbase.ref.version} does not provide the required bin/qmake tool"
            )

        # Native build (build == host == OHOS/aarch64): qmake runs on the target
        # machine, so the OHOS clang from the profile is used directly.
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cxx = compiler_executables.get("cpp") or compiler_executables.get("cxx") or "clang++"

        build_env = Environment()
        build_env.define("QTDIR", qtbase_pkg)
        build_env.prepend_path("PATH", os.path.join(qtbase_pkg, "bin"))
        build_env.append("LD_LIBRARY_PATH", os.path.join(qtbase_pkg, "lib"))
        jobs = self.conf.get("tools.build:jobs", default=4, check_type=int)

        with build_env.vars(self).apply():
            self.run(
                f"cd {shlex.quote(self.source_folder)} && "
                f"{shlex.quote(qmake)} -spec linux-clang "
                f"QMAKE_CXX={shlex.quote(cxx)} QMAKE_LINK={shlex.quote(cxx)} "
                "KoncludeWithoutRedland.pro",
                cwd=self.source_folder,
            )
            # QMAKE_STRIP="" keeps the debug-less release binary unmodified so the
            # OHOS ELF signing step in CI sees exactly the bytes we validated.
            self.run(
                f"make -j{jobs} QMAKE_STRIP=",
                cwd=self.source_folder,
            )

    def package(self):
        copy(self, "Konclude",
             src=os.path.join(self.source_folder, "Release"),
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "LGPL-3.0.txt",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        # Upstream configuration files are referenced by the documented
        # invocations (`-c Configs/default-config.xml`), so they ship with the tool.
        copy(self, "*.xml",
             src=os.path.join(self.source_folder, "Configs"),
             dst=os.path.join(self.package_folder, "res", "konclude", "Configs"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "konclude")
