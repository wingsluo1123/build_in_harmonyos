import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class JdimTestConan(ConanFile):
    """Consumer test for the jdim application package.

    jdim ships an application, so the consumer contract is the installed
    binary's observable behaviour: ``jdim --version`` must print the program
    name, the upstream version and the full configure line captured at build
    time.  That configure line is real evidence that the recipe's feature
    switches (--with-sessionlib=xsmp / --with-migemo / --with-alsa) were
    actually applied to this build.
    """

    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["jdim"].package_folder
        binary = os.path.join(package_folder, "bin", "jdim")
        if not os.path.isfile(binary):
            raise ConanException("jdim binary not found in the package: %s" % binary)
        with open(binary, "rb") as handle:
            assert handle.read(4) == b"\x7fELF", "jdim is not an ELF binary: %s" % binary

        if not can_run(self):
            self.output.info("cross build: jdim ELF present, execution skipped: %s" % binary)
            return

        # VirtualRunEnv's LD_LIBRARY_PATH does not list every runtime library
        # of the package (observed: libgnutls.so.30 missing), so put the
        # dependency lib dirs on the command line as well -- same reason as in
        # the recipe's build().
        libdirs = []
        for dep in self.dependencies.host.values():
            folder = dep.package_folder
            if not folder:
                continue
            for relative in ("lib", "lib64"):
                candidate = os.path.join(folder, relative)
                if os.path.isdir(candidate) and candidate not in libdirs:
                    libdirs.append(candidate)

        shell = os.environ.get("SHELL") or "/bin/sh"
        script = os.path.join(self.recipe_folder, "test.sh")
        self.run('LD_LIBRARY_PATH="%s${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" '
                 '"%s" "%s" "%s"' % (":".join(libdirs), shell, script, binary),
                 env="conanrun")
