#!/usr/bin/env python3
"""Conan recipe for IRAF 2.18.1 (Make/SPP/Ratfor/F2C native bootstrap)."""
import os
import json
import re
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, save
from conan.tools.layout import basic_layout


def _link_probe(compiler, directory, name, source, symbol=None, header=None):
    """Compile and link only; unavailable capabilities must have a known diagnostic."""
    os.makedirs(directory, exist_ok=True)
    source_path = os.path.join(directory, name + ".c")
    with open(source_path, "w", encoding="utf-8", newline="\n") as stream:
        stream.write(source)
    command = [compiler, "-D_GNU_SOURCE", "-O0", "-Werror=implicit-function-declaration",
               source_path, "-o", os.path.join(directory, name + ".e")]
    env = os.environ.copy()
    env["LC_ALL"] = "C"
    env["TMPDIR"] = os.path.abspath(directory)
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, encoding="utf-8", errors="replace", env=env, timeout=90)
    detail = {"command": command, "exit_code": result.returncode, "output": result.stdout,
              "temporary_directory": env["TMPDIR"]}
    if result.returncode == 0:
        return True, detail
    resource_errors = ("out of memory", "cannot allocate memory", "no space left on device",
                       "permission denied", "operation not permitted", "read-only file system",
                       "disk quota exceeded", "too many open files", "file table overflow",
                       "resource temporarily unavailable", "internal compiler error",
                       "unable to make temporary file", "cannot execute", "unable to execute",
                       "cannot fork", "failed to fork", "segmentation fault", "bus error", "killed")
    if (result.returncode != 1 or any(error in result.stdout.lower() for error in resource_errors)
            or re.search(r"\bsignal\s+[0-9]+\b", result.stdout, re.IGNORECASE)):
        raise RuntimeError("Compiler execution failed during " + name + ": " + result.stdout)
    missing_symbol = symbol and re.search(
        r"(?:undefined (?:symbol|reference)|undeclared function|undeclared identifier|"
        r"implicit declaration of function)[^\n]*\b" + re.escape(symbol) + r"\b", result.stdout)
    missing_header = header and any(text in result.stdout for text in (
        "'" + header + "' file not found", '"' + header + '" file not found',
        header + ": No such file or directory"))
    if missing_symbol or missing_header:
        # A capability error cannot excuse another compiler/linker error in
        # the same invocation. Only accept its normal driver summary.
        for line in result.stdout.splitlines():
            if not re.search(r"\b(?:fatal\s+)?error:|undefined (?:symbol|reference)", line):
                continue
            expected_symbol = symbol and re.search(
                r"(?:undefined (?:symbol|reference)|undeclared function|undeclared identifier|"
                r"implicit declaration of function)[^\n]*\b" + re.escape(symbol) + r"\b", line)
            expected_header = header and any(text in line for text in (
                "'" + header + "' file not found", '"' + header + '" file not found',
                header + ": No such file or directory"))
            driver_summary = re.search(
                r"(?:clang(?:-[0-9]+)?|collect2): error: (?:linker command failed with exit code 1"
                r"(?: \(use -v to see invocation\))?|ld returned 1 exit status)\s*$", line)
            if not (expected_symbol or expected_header or driver_summary):
                raise RuntimeError("Additional compiler failure during " + name + ": " + result.stdout)
        return False, detail
    raise RuntimeError("Unexpected compiler failure during " + name + ": " + result.stdout)


def _detect_host_features(compiler, directory):
    """Select libc interfaces by real link probes, independently of platform macros."""
    directory = os.path.abspath(directory)
    probes = {}
    _, probes["compiler"] = _link_probe(compiler, directory, "compiler", "int main(void){return 0;}\n")
    selected = None
    for symbol in ("sigsetjmp", "__sigsetjmp"):
        # Do not include setjmp.h: its alias would hide the actual exported symbol.
        code = ("extern int " + symbol + "(void *, int);\n"
                "int main(void){char buffer[1024];return " + symbol + "(buffer,0);}\n")
        available, probes[symbol] = _link_probe(compiler, directory, symbol, code, symbol=symbol)
        if available:
            selected = symbol
            break
    if selected is None:
        raise RuntimeError("Neither sigsetjmp nor __sigsetjmp is linkable; no context shim is generated")
    rcmd, probes["rcmd"] = _link_probe(
        compiler, directory, "rcmd", "#include <netdb.h>\n"
        'int main(void){char *host=0;return rcmd(&host,0,"","","",0);}\n', symbol="rcmd")
    fpu, probes["fpu_control"] = _link_probe(
        compiler, directory, "fpu_control", "#include <fpu_control.h>\nint main(void){return 0;}\n",
        header="fpu_control.h")
    features = {"compiler": compiler, "sigsetjmp_symbol": selected, "use_ssh_rcmd": not rcmd,
                "has_fpu_control_h": fpu, "probes": probes}
    with open(os.path.join(directory, "features.json"), "w", encoding="utf-8", newline="\n") as stream:
        json.dump(features, stream, indent=2)
        stream.write("\n")
    return features


class IrafConan(ConanFile):
    name = "iraf"
    version = "2.18.1"
    package_type = "application"
    license = "MIT"
    description = "Image Reduction and Analysis Facility, including the SPP compiler and NOAO packages"
    homepage = "https://github.com/iraf-community/iraf"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "f77_parallel.py", self.recipe_folder, self.export_sources_folder)
        copy(self, "f2c_launcher.py", self.recipe_folder, self.export_sources_folder)

    def requirements(self):
        self.requires("readline/8.3")
        # The installed xc compiler links new programs with zlib. Its archive
        # must remain available when installing the prebuilt application.
        self.requires("zlib/1.3.1", run=True)

    def build_requirements(self):
        self.tool_requires("flex/2.6.4.2")
        self.tool_requires("bison/3.8.2")
        self.tool_requires("m4/1.4.19")

    def validate(self):
        if self.settings.os != "OHOS" or self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("This recipe is validated for native OHOS armv8")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()

    def _environment(self):
        env = Environment()
        tools_dir = os.path.join(self.build_folder, "tools")
        os.makedirs(tools_dir, exist_ok=True)
        yacc = os.path.join(tools_dir, "yacc")
        save(self, yacc, '#!/bin/sh\nexec bison -y "$@"\n')
        os.chmod(yacc, 0o755)
        env.prepend_path("PATH", tools_dir)
        env.define("BISON_PKGDATADIR", os.path.join(self.dependencies.build["bison"].package_folder,
                                                   "share", "bison"))
        env.define("M4", os.path.join(self.dependencies.build["m4"].package_folder, "bin", "m4"))
        with open(os.path.join(self.build_folder, "host-probes", "features.json"), encoding="utf-8") as stream:
            features = json.load(stream)
        compiler = features["compiler"]
        env.define("CC", compiler)
        compilers = self.conf.get("tools.build:compiler_executables", default={})
        for name in ("ar", "ranlib", "nm", "strip"):
            tool = compilers.get(name) or os.path.join(os.path.dirname(os.path.realpath(compiler)), "llvm-" + name)
            if not os.path.isfile(tool):
                tool = shutil.which("llvm-" + name)
            if not tool:
                raise ConanException("The configured SDK must provide llvm-" + name)
            wrapper = os.path.join(tools_dir, name)
            save(self, wrapper, "#!/bin/sh\nexec " + shlex.quote(tool) + ' "$@"\n')
            os.chmod(wrapper, 0o755)
        env.define("IRAFARCH", "linux64")
        temp = os.path.join(self.build_folder, "tmp")
        os.makedirs(temp, exist_ok=True)
        env.define("TMPDIR", temp)
        env.define("tmp", temp + "/")
        env.define("F2CFLAGS", "-KRw8 -Nn802 -cf -T" + temp)
        env.define("IRAF_F77_SERIAL", os.path.join(self.source_folder, "unix", "hlib", "f77.sh"))
        env.define("IRAF_F77_WORKERS", str(self._jobs()))
        env.define("IRAF_F2C_REAL", os.path.join(self.source_folder, "unix", "bin.linux64", "f2c.e"))
        includes, links, libs = [], [], []
        for dep in self.dependencies.host.values():
            info = dep.cpp_info.aggregated_components()
            includes += ["-I" + d for d in info.includedirs]
            links += ["-L" + d for d in info.libdirs]
            libs += ["-l" + lib for lib in info.libs + info.system_libs]
        defines = ["-DIRAF_SIGSETJMP=" + features["sigsetjmp_symbol"]]
        if features["use_ssh_rcmd"]:
            defines.append("-DIRAF_USE_SSH_RCMD=1")
        env.define("CPPFLAGS", " ".join(includes + defines))
        # mkpkg invokes xc directly: it must consume transitive link metadata.
        env.define("LDFLAGS", " ".join(links + libs))
        env.define("XC_CFLAGS", "-O2 " + " ".join(includes + defines))
        env.define("XC_LFLAGS", " ".join(links + libs))
        return env

    def _jobs(self):
        return max(1, min(4, self.conf.get("tools.build:jobs", default=4, check_type=int)))

    def build(self):
        apply_conandata_patches(self)
        compiler = (self.conf.get("tools.build:compiler_executables", default={}).get("c")
                    or shutil.which("clang") or shutil.which("cc") or "cc")
        compiler = os.path.abspath(shutil.which(compiler) or compiler)
        try:
            with VirtualBuildEnv(self).vars().apply():
                features = _detect_host_features(compiler, os.path.join(self.build_folder, "host-probes"))
        except (OSError, subprocess.SubprocessError, RuntimeError) as error:
            raise ConanException("Host capability probes failed: " + str(error)) from error
        self.output.info("IRAF_HOST_FEATURES=" + json.dumps(
            {key: value for key, value in features.items() if key != "probes"}, sort_keys=True))
        scheduler = os.path.join(self.source_folder, "f77_parallel.py")
        os.chmod(scheduler, 0o755)
        f2c_launcher = os.path.join(self.source_folder, "f2c_launcher.py")
        os.chmod(f2c_launcher, 0o755)
        makevars = " tmp=" + shlex.quote(os.path.join(self.build_folder, "tmp") + "/")
        makevars += " F77=" + shlex.quote(scheduler)
        makevars += " F2C=" + shlex.quote(f2c_launcher)
        # Expand PATH after VirtualBuildEnv activates; its bison package also
        # exports a non-relocatable yacc script, so our shim must come first.
        makevars += " PATH=" + shlex.quote(os.path.join(self.build_folder, "tools")) + ':"$PATH"'
        with self._environment().vars(self).apply():
            self.run("make -j" + str(self._jobs()) + makevars, cwd=self.source_folder, env="conanbuild")
            self.run("timeout 1800 make test" + makevars + " > upstream-test.log 2>&1",
                     cwd=self.source_folder, env="conanbuild")
            log = open(os.path.join(self.source_folder, "upstream-test.log"), encoding="utf-8").read()
            self.output.info(log)
            summaries = []
            for section in log.split("Test summary:")[1:]:
                rows = []
                for line in section.splitlines():
                    if not re.fullmatch(r"\s*\d+\s+(?:passed|failed|skipped|xfailed)(?:,\s*\d+\s+(?:passed|failed|skipped|xfailed))*\s*", line):
                        break
                    rows.append(line.strip())
                summaries.append(", ".join(rows))
            if len(summaries) != 2:
                raise ConanException("Both upstream make test invocations must complete")
            total = sum(int(n) for row in summaries for n in re.findall(r"(\d+)\s+\w+", row))
            if total != 143 or any(re.search(r"\bfailed\b", row) for row in summaries):
                raise ConanException("Unexpected upstream test inventory/result: " + str(summaries))

    def package(self):
        # The upstream install target preserves all runtime resources, headers,
        # and compiler libraries, then applies its production strip lists.
        with self._environment().vars(self).apply():
            self.run("make install prefix=" + shlex.quote(self.package_folder)
                     + " sysconfdir=" + shlex.quote(os.path.join(self.package_folder, "etc", "iraf"))
                     + " tmp=" + shlex.quote(os.path.join(self.build_folder, "tmp") + "/"),
                     cwd=self.source_folder, env="conanbuild")
        copy(self, "COPYRIGHT", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "*", os.path.join(self.source_folder, "licenses"),
             os.path.join(self.package_folder, "licenses", "upstream"))
        names = ("irafcl", "cl", "ecl", "mkiraf", "mkpkg", "rmbin", "rmfiles",
                 "rtar", "sgidispatch", "wtar", "xc", "xyacc", "f2c", "xpp", "rpp")
        for name in names:
            dest = os.path.join(self.package_folder, "bin", name)
            if os.path.lexists(dest):
                os.unlink(dest)
            if name in ("irafcl", "cl", "ecl"):
                target = '"${iraf}unix/hlib/irafcl.sh"'
                if name == "cl":
                    target += " -c"
            elif name == "mkiraf":
                target = '"${iraf}unix/hlib/mkiraf.sh"'
            else:
                target = '"${iraf}unix/bin.linux64/' + name + '.e"'
            wrapper = '''#!/bin/sh
export iraf="$(CDPATH= cd -- "$(dirname -- "$0")/../lib/iraf" && pwd)/"
export IRAFARCH=linux64
: "${TMPDIR:=${HOME}/.cache/iraf/tmp}"
mkdir -p "$TMPDIR" || exit 1
export TMPDIR tmp="$TMPDIR/"
export F2C="${iraf}unix/bin.linux64/f2c.e"
export F2CFLAGS="${F2CFLAGS:--KRw8 -Nn802 -cf} -T$TMPDIR"
exec ''' + target + ' "$@"\n'
            save(self, dest, wrapper)
            os.chmod(dest, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
        links, includes = [], []
        info = self.dependencies["zlib"].cpp_info.aggregated_components()
        includes += ["-I" + d for d in info.includedirs]
        links += ["-L" + d for d in info.libdirs]
        links += ["-l" + lib for lib in info.libs + info.system_libs]
        # xc is an installed compiler driver, so its dependencies must also be
        # discoverable when a consumer compiles a new SPP program.
        for env in (self.runenv_info, self.buildenv_info):
            env.append("XC_LFLAGS", " ".join(links))
            env.append("XC_CFLAGS", " ".join(includes))
