#!/usr/bin/env python3
"""Conan test_package — ocamlbuild 0.16.1 (consumer view).

Recreates the OHOS toolchain shims (see the recipe docstring for the full
rationale: missing GNU `as`, baked dead C compiler path, dangling bytecode
shebangs, ocamlmklib baked path, ELF .codesign enforcement, findlib topfind /
conf gaps) and then uses the PACKAGED ocamlbuild binary to build and run two
small projects on the device:

  1. a plain project (no findlib): hello.native + hello.byte built and run;
  2. a HarmonyOS e2e consumer case: findlib-driven build
     (`-use-ocamlfind -package str`) of a native binary, run on the device
     with assertions on its output.
"""
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException


class OcamlbuildTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("ocaml/4.14.1.1.4")
        self.requires("findlib/1.9.8")

    def layout(self):
        self.folders.build = "."
        self.folders.source = "."

    def generate(self):
        pass

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

    def _make_shims(self):
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

        write("as", "#!/bin/sh\nexec %s -c \"$@\"\n" % shlex.quote(cc))
        write("ocaml", "#!/bin/sh\nexec %s %s -I %s -I %s \"$@\"\n" % (
            shlex.quote(os.path.join(ocaml_bin, "ocamlrun")),
            shlex.quote(os.path.join(ocaml_bin, "ocaml")),
            shlex.quote(find_lib), shlex.quote(shim)))
        for tool in ("ocamlc", "ocamlc.opt"):
            write(tool, "#!/bin/sh\nexec %s -use-runtime %s -cc %s \"$@\"\n" % (
                shlex.quote(os.path.join(ocaml_bin, tool)),
                shlex.quote(os.path.join(ocaml_bin, "ocamlrun")),
                shlex.quote(cc)))
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
                             shlex.quote(cc),
                             shlex.quote(os.path.join(shim, "sign-elf")))
        for tool in ("ocamlopt", "ocamlopt.opt"):
            write(tool, opt_body % tool)

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

        with open(os.path.join(shim, "ld.conf"), "w") as f:
            f.write(os.path.join(ocaml_lib, "stublibs") + "\n")
        with open(os.path.join(shim, "ocamlfind.conf"), "w") as f:
            f.write('destdir="%s"\npath="%s"\nldconf="%s"\n'
                    'ocamlc="ocamlc.opt"\nocamlopt="ocamlopt.opt"\n'
                    'ocamldep="ocamldep.opt"\nocamldoc="ocamldoc.opt"\n'
                    % (find_lib, find_lib, os.path.join(shim, "ld.conf")))
        with open(os.path.join(shim, "topfind"), "w") as f:
            f.write('#directory "%s/findlib";;\n#load "findlib.cma";;\n'
                    '#load "findlib_top.cma";;\n' % find_lib)

        env = {
            "OCAMLLIB": ocaml_lib,
            "CAML_LD_LIBRARY_PATH": os.path.join(ocaml_lib, "stublibs"),
            "OCAMLFIND_CONF": os.path.join(shim, "ocamlfind.conf"),
            "OCAMLPATH": find_lib + ":" + ocaml_lib,
            "PATH": shim + os.pathsep + ocaml_bin + os.pathsep + find_bin
                    + os.pathsep + os.environ.get("PATH", ""),
        }
        return shim, ocaml_lib, ocaml_bin, find_lib, find_bin, cc, env

    def test(self):
        pkg = self.dependencies[self.tested_reference_str]
        shim, ocaml_lib, ocaml_bin, find_lib, find_bin, cc, env = \
            self._make_shims()
        test_sh = os.path.join(self.source_folder, "test.sh")
        if not os.path.isfile(test_sh):
            raise ConanException("test_package/test.sh missing")
        args = [test_sh, pkg.package_folder, ocaml_lib, ocaml_bin,
                find_lib, find_bin, shim, cc]
        self.run('sh "%s"' % '" "'.join(args),
                 env=["%s=%s" % (k, v) for k, v in env.items()])
        self.output.info("ocamlbuild test_package: ALL PASS")
