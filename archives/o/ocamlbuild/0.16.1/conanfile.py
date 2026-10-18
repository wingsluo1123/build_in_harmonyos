#!/usr/bin/env python3
"""Conan recipe — ocamlbuild 0.16.1

ocamlbuild is the OCaml build system with built-in rules for OCaml projects.
Upstream builds with a GNU Makefile driven by `configure.make` (which includes
`$(ocamlc -where)/Makefile.config`) and a self-contained OCaml toolchain.
OHOS/aarch64 adaptations (all verified on the physical device):

  - registry ocaml package defect #1: the baked assembler is a bare `as`,
    which does not exist on OHOS. A tiny `as` shim forwards to the OHOS clang
    with `-c` (clang integrated assembler handles GAS aarch64).
  - registry ocaml package defect #2: the baked C compiler is the dead CI
    worker path /data/service/hnp/bin/clang. `ocamlc`/`ocamlopt` shims add
    `-cc <OHOS clang>`; `ocamlopt` additionally adds `-ccopt -shared` when a
    `-shared` link is requested (OCaml drops -shared when -cc is used).
  - registry ocaml package defect #3: bytecode shebangs embed the build-time
    cache path. `ocamlc` shims add `-use-runtime <real ocamlrun>`, and the
    `ocaml` toplevel shim runs the toplevel through `ocamlrun` (the installed
    `ocaml` launcher itself has a dangling shebang).
  - registry ocaml package defect #4: `ocamlmklib` ignores -cc and directly
    executes the baked dead compiler path. When that path is missing, a
    string-patched copy (`<dead path>` -> `clang` + padding, resolved from
    PATH) is installed in the shim dir and re-signed. On CI machines where
    the hnp path exists the original tool is used unchanged.
  - OHOS refuses to execute ELF binaries whose lld-generated `.codesign`
    section is not accepted (EPERM); freshly linked executables produced by
    the shims are re-signed with the SDK `binary-sign-tool` (-selfSign 1).
  - registry findlib package gaps: `topfind` script is not installed and its
    `ocamlfind.conf` points at the build-time cache. The shim dir provides a
    minimal `topfind` (loads findlib.cma + findlib_top.cma) and a corrected
    `ocamlfind.conf`/`ld.conf`; OCAMLPATH points at findlib + ocaml libdirs.
  - The upstream testsuite executes `ocamlbuild.byte` directly (fixed shebang
    via -use-runtime) and loads the tests through the `ocaml` shim; the
    findlib-only tests need the corrected ocamlfind configuration above.

Upstream tests run in build(): testsuite/internal.ml (44 tests),
testsuite/findlibonly.ml (3 tests), testsuite/external.ml (3 tests, all
skipped by upstream requirement guards because camlp4/camlp4.macro/menhir are
not available). No upstream source file is modified.
"""
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (get, copy, apply_conandata_patches,
                               export_conandata_patches)


class OcamlbuildConan(ConanFile):
    name = "ocamlbuild"
    version = "0.16.1"
    description = ("OCamlbuild is a build system with builtin rules to easily "
                   "build most OCaml projects")
    license = "LGPL-2.0-or-later WITH OCaml-LGPL-linking-exception"
    homepage = "https://github.com/ocaml/ocamlbuild"
    url = ""  # CI fills this
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    # OCaml artifacts are static by nature; option kept for interface parity.
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Toolchain + findlib (ocamlfind is a with-test dependency upstream
        # and is used by ocamlbuild consumers via -use-ocamlfind).
        self.requires("ocaml/4.14.1.1.4")
        self.requires("findlib/1.9.8")

    def layout(self):
        self.folders.build = "."
        self.folders.source = "."

    def source(self):
        get(self, strip_root=True, **self.conan_data["sources"][self.version])

    def generate(self):
        pass  # GNU Make + configure.make, no autotools/CMake toolchain

    # ------------------------------------------------------------------ tools
    @staticmethod
    def _find_tool(candidates):
        for c in candidates:
            if c and os.path.isfile(c) and os.access(c, os.X_OK):
                return c
        for c in candidates:
            if c:
                w = shutil.which(c)
                if w:
                    return w
        return ""

    def _toolchain(self):
        """Return (cc, env_prefix) after installing the OHOS shim dir."""
        ocaml_pkg = self.dependencies["ocaml/4.14.1.1.4"]
        find_pkg = self.dependencies["findlib/1.9.8"]
        ocaml_bin = os.path.join(ocaml_pkg.package_folder, "bin")
        ocaml_lib = os.path.join(ocaml_pkg.package_folder, "lib", "ocaml")
        find_bin = os.path.join(find_pkg.package_folder, "bin")
        find_lib = os.path.join(find_pkg.package_folder, "lib", "ocaml")

        cc = (self.conf.get("tools.build:compiler_executables", default={},
                            check_type=dict).get("c")
              or os.environ.get("CC") or "clang")
        cc_dir = os.path.dirname(cc)
        objcopy = self._find_tool([os.path.join(cc_dir, "llvm-objcopy"),
                                   "llvm-objcopy", "objcopy"])
        readelf = self._find_tool([os.path.join(cc_dir, "llvm-readelf"),
                                   "llvm-readelf", "readelf"])
        sign = self._find_tool([
            os.path.join(cc_dir, "..", "..", "..", "bin", "binary-sign-tool"),
            "/data/service/hnp/bin/binary-sign-tool",
            "binary-sign-tool",
        ])

        shim = os.path.join(self.build_folder, ".ohc-toolchain")
        os.makedirs(shim, exist_ok=True)

        def write(name, content):
            p = os.path.join(shim, name)
            with open(p, "w") as f:
                f.write(content)
            os.chmod(p, 0o755)

        # as shim -> clang -c
        write("as", "#!/bin/sh\nexec %s -c \"$@\"\n" % shlex.quote(cc))

        # ocaml toplevel shim (installed launcher has a dangling shebang);
        # -I makes `#use "topfind"` resolvable from the shim dir
        write("ocaml", "#!/bin/sh\nexec %s %s -I %s -I %s \"$@\"\n" % (
            shlex.quote(os.path.join(ocaml_bin, "ocamlrun")),
            shlex.quote(os.path.join(ocaml_bin, "ocaml")),
            shlex.quote(find_lib), shlex.quote(shim)))

        # bytecode compilers: fix shebang runtime + C compiler override
        for tool in ("ocamlc", "ocamlc.opt"):
            write(tool, "#!/bin/sh\nexec %s -use-runtime %s -cc %s \"$@\"\n" % (
                shlex.quote(os.path.join(ocaml_bin, tool)),
                shlex.quote(os.path.join(ocaml_bin, "ocamlrun")),
                shlex.quote(cc)))

        # sign helper for freshly linked executables
        write("sign-elf", (
            "#!/bin/sh\n"
            "f=\"$1\"\n"
            "[ -f \"$f\" ] || exit 0\n"
            "case \"$f\" in *.cmxs|*.so|*.o|*.a|*.cma|*.cmxa|*.cmo|*.cmx) exit 0 ;; esac\n"
            "head -c4 \"$f\" | grep -q ELF || exit 0\n"
            "%s -l \"$f\" 2>/dev/null | grep -q INTERP || exit 0\n"
            "%s --remove-section .codesign \"$f\" 2>/dev/null\n"
            "if %s sign -inFile \"$f\" -outFile \"$f.signed.tmp\" -selfSign 1 >/dev/null 2>&1; then\n"
            "  mv \"$f.signed.tmp\" \"$f\" && chmod 755 \"$f\"\n"
            "else\n"
            "  rm -f \"$f.signed.tmp\"\n"
            "fi\n"
            "exit 0\n") % (shlex.quote(readelf), shlex.quote(objcopy),
                           shlex.quote(sign or "binary-sign-tool")))

        # native compilers: -cc override (+ restore -shared), sign outputs
        opt_body = (
            "#!/bin/sh\n"
            "EXTRA=\"\"\n"
            "case \" $* \" in *\" -shared \"*) EXTRA=\"-ccopt -shared\" ;; esac\n"
            "%s -cc %s $EXTRA \"$@\"\n"
            "rc=$?\n"
            "if [ $rc -eq 0 ]; then\n"
            "  out=\"\"; prev=\"\"\n"
            "  for a in \"$@\"; do [ \"$prev\" = \"-o\" ] && out=\"$a\"; prev=\"$a\"; done\n"
            "  [ -n \"$out\" ] && %s \"$out\"\n"
            "fi\n"
            "exit $rc\n") % (shlex.quote(os.path.join(ocaml_bin, "%s")),
                             shlex.quote(cc), shlex.quote(os.path.join(shim, "sign-elf")))
        for tool in ("ocamlopt", "ocamlopt.opt"):
            write(tool, opt_body % tool)

        # ocamlmklib ignores -cc and runs the baked CI compiler path directly.
        # Patch a private copy only when that path is missing on this machine.
        baked = b"/data/service/hnp/bin/clang"
        if not os.path.exists("/data/service/hnp/bin/clang"):
            for tool in ("ocamlmklib", "ocamlmklib.opt"):
                src = os.path.join(ocaml_bin, tool)
                data = open(src, "rb").read()
                if baked in data:
                    dst = os.path.join(shim, tool)
                    with open(dst, "wb") as f:
                        f.write(data.replace(baked,
                                             b"clang" + b" " * (len(baked) - 5)))
                    os.chmod(dst, 0o755)
                    self.run("%s --remove-section .codesign %s" % (
                        shlex.quote(objcopy), shlex.quote(dst)),
                        env="conanbuild")
                    tmp = dst + ".signed.tmp"
                    self.run("%s sign -inFile %s -outFile %s -selfSign 1" % (
                        shlex.quote(sign), shlex.quote(dst), shlex.quote(tmp)),
                        env="conanbuild")
                    os.replace(tmp, dst)
                    os.chmod(dst, 0o755)

        # findlib configuration for this package layout
        with open(os.path.join(shim, "ld.conf"), "w") as f:
            f.write(os.path.join(ocaml_lib, "stublibs") + "\n")
        with open(os.path.join(shim, "ocamlfind.conf"), "w") as f:
            f.write('destdir="%s"\npath="%s"\nldconf="%s"\n'
                    'ocamlc="ocamlc.opt"\nocamlopt="ocamlopt.opt"\n'
                    'ocamldep="ocamldep.opt"\nocamldoc="ocamldoc.opt"\n'
                    % (find_lib, find_lib, os.path.join(shim, "ld.conf")))
        # minimal topfind (registry findlib package does not install the
        # upstream toplevel script); loads findlib's toplevel integration
        with open(os.path.join(shim, "topfind"), "w") as f:
            f.write('#directory "%s/findlib";;\n#load "findlib.cma";;\n'
                    '#load "findlib_top.cma";;\n' % find_lib)

        env_prefix = (
            "OCAMLLIB=%s CAML_LD_LIBRARY_PATH=%s "
            "OCAMLFIND_CONF=%s OCAMLPATH=%s:%s PATH=%s:%s:%s:$PATH " % (
                shlex.quote(ocaml_lib),
                shlex.quote(os.path.join(ocaml_lib, "stublibs")),
                shlex.quote(os.path.join(shim, "ocamlfind.conf")),
                shlex.quote(find_lib), shlex.quote(ocaml_lib),
                shlex.quote(shim), shlex.quote(ocaml_bin),
                shlex.quote(find_bin),
            )
        )
        return cc, env_prefix

    # ------------------------------------------------------------------ build
    def build(self):
        apply_conandata_patches(self)  # no-op: upstream builds unmodified
        cc, env_prefix = self._toolchain()
        prefix = self.package_folder

        # 1) configuration (configure.make -> Makefile.config + config module)
        self.run(
            "%smake -f configure.make all "
            "OCAMLBUILD_PREFIX=%s OCAMLBUILD_BINDIR=%s OCAMLBUILD_LIBDIR=%s "
            "OCAMLBUILD_MANDIR=%s OCAML_NATIVE=true OCAML_NATIVE_TOOLS=true"
            % (env_prefix, shlex.quote(prefix),
               shlex.quote(os.path.join(prefix, "bin")),
               shlex.quote(os.path.join(prefix, "lib", "ocaml")),
               shlex.quote(os.path.join(prefix, "man"))),
            env="conanbuild")

        # 2) bytecode + native + man
        self.run("%smake all" % env_prefix, env="conanbuild")

        # 3) upstream testsuite (R51): 44 internal + 3 findlib-only tests run;
        #    the 3 external tests are skipped by upstream requirement guards
        #    (camlp4/camlp4.macro/menhir packages are not in the registry).
        for group in ("test-internal", "test-findlibonly", "test-external"):
            self.run("%smake %s" % (env_prefix, group), env="conanbuild")

    def package(self):
        dest = os.path.join(self.build_folder, "dest_install")
        self.run('make install CHECK_IF_PREINSTALLED=false DESTDIR="%s"' % dest,
                 env="conanbuild")
        src_base = os.path.join(dest, self.package_folder.lstrip("/"))
        if not os.path.isdir(src_base):
            src_base = dest
        copy(self, "*", src_base, self.package_folder)
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

        bin_dir = os.path.join(self.package_folder, "bin")
        for fname in ("ocamlbuild", "ocamlbuild.byte", "ocamlbuild.native"):
            p = os.path.join(bin_dir, fname)
            if not os.path.isfile(p):
                raise ConanException("mandatory tool missing: %s" % p)
            os.chmod(p, 0o755)
        # sanity: packaged artifacts must be real files
        for root, _dirs, files in os.walk(self.package_folder):
            for fname in files:
                p = os.path.join(root, fname)
                if os.path.islink(p):
                    raise ConanException("package artifact is a symlink: %s" % p)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib/ocaml/ocamlbuild"]
        self.cpp_info.includedirs = ["lib/ocaml/ocamlbuild"]
        self.buildenv_info.append_path(
            "PATH", os.path.join(self.package_folder, "bin"))
        self.buildenv_info.append_path(
            "OCAMLPATH", os.path.join(self.package_folder, "lib", "ocaml"))
        self.runenv_info.append_path(
            "PATH", os.path.join(self.package_folder, "bin"))
