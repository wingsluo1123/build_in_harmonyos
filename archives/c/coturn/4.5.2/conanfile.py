import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.env import Environment


class CoturnConan(ConanFile):
    name = "coturn"
    version = "4.5.2"
    description = "Free open source implementation of TURN and STUN Server"
    license = "MIT"
    homepage = "https://github.com/coturn/coturn"
    settings = "os", "compiler", "build_type", "arch"

    # PkgConfigDeps generates .pc files for Conan dependencies;
    # coturn configure uses pkg-config to find sqlite3.
    # OpenSSL and libevent are passed via SSL_CFLAGS/SSL_LIBS and
    # EVENT_CFLAGS/EVENT_LIBS env vars (coturn configure supports this),
    # because their .pc file names (openssl.pc, libevent.pc) don't match
    # the names coturn expects (libcrypto, libssl, libevent_core, etc.).
    generators = "PkgConfigDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # R27: Conan dependencies with @ohpcd/stable channel
        self.requires("openssl/3.5.6@ohpcd/stable")
        self.requires("libevent/2.1.12@ohpcd/stable")
        self.requires("sqlite3/3.49.1@ohpcd/stable")

    def layout(self):
        self.folders.build = "."
        self.folders.source = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        env = Environment()
        # R10: /tmp is read-only on OHOS, use $TMPDIR (E002)
        env.define_path("TMPDIR", os.environ.get("TMPDIR", os.path.expanduser("~/tmp")))
        # E075: C_INCLUDE_PATH causes pkg-config --cflags to return empty
        env.unset("C_INCLUDE_PATH")
        env.unset("CPLUS_INCLUDE_PATH")

        # Collect dependency lib paths for LIBRARY_PATH and LD_LIBRARY_PATH
        for dep_name in ["openssl", "libevent", "sqlite3"]:
            dep = self.dependencies[dep_name]
            pkg_folder = dep.package_folder
            for d in dep.cpp_info.libdirs:
                lib_dir = d if os.path.isabs(d) else os.path.join(pkg_folder, d)
                env.append_path("LIBRARY_PATH", lib_dir)
                env.append_path("LD_LIBRARY_PATH", lib_dir)

        # OpenSSL: pass flags via SSL_CFLAGS/SSL_LIBS (coturn configure supports this)
        openssl = self.dependencies["openssl"]
        openssl_folder = openssl.package_folder
        openssl_incs = [d if os.path.isabs(d) else os.path.join(openssl_folder, d)
                        for d in openssl.cpp_info.includedirs]
        openssl_lib_dirs = [d if os.path.isabs(d) else os.path.join(openssl_folder, d)
                            for d in openssl.cpp_info.libdirs]
        env.define("SSL_CFLAGS", " ".join(f"-I{d}" for d in openssl_incs))
        env.define("SSL_LIBS", " ".join(f"-L{d}" for d in openssl_lib_dirs)
                   + " -lssl -lcrypto -ldl -lpthread")

        # libevent: pass flags via EVENT_CFLAGS/EVENT_LIBS (coturn configure supports this)
        libevent = self.dependencies["libevent"]
        libevent_folder = libevent.package_folder
        libevent_incs = [d if os.path.isabs(d) else os.path.join(libevent_folder, d)
                         for d in libevent.cpp_info.includedirs]
        libevent_lib_dirs = [d if os.path.isabs(d) else os.path.join(libevent_folder, d)
                             for d in libevent.cpp_info.libdirs]
        env.define("EVENT_CFLAGS", " ".join(f"-I{d}" for d in libevent_incs))
        env.define("EVENT_LIBS", " ".join(f"-L{d}" for d in libevent_lib_dirs)
                   + " -levent -levent_extra -levent_openssl -levent_pthreads")

        # PKG_CONFIG_PATH: point to Conan-generated .pc files (PkgConfigDeps)
        # Used by coturn configure to find sqlite3 via pkg-config
        env.define_path("PKG_CONFIG_PATH", self.generators_folder)

        envvars = env.vars(self)
        envvars.save_script("conanbuildenv")

    def build(self):
        apply_conandata_patches(self)
        self.run("sh ./configure --prefix=" + self.package_folder, env="conanbuildenv")
        njobs = max(os.cpu_count() // 2, 1)
        self.run(f"make -j{njobs}", env="conanbuildenv")
        # Upstream official tests (RFC 5769 compliance)
        self.run("make check", env="conanbuildenv")

    def package(self):
        self.run("make install", env="conanbuildenv")

    def package_info(self):
        self.cpp_info.libs = ["turnclient"]
        # ns_turn_ioaddr.h includes "ns_turn_defs.h" which is in include/turn/
        # (one level up from include/turn/client/), so both dirs are needed
        self.cpp_info.includedirs = ["include", "include/turn"]

        # Propagate LD_LIBRARY_PATH for shared dependencies (libevent is dynamic).
        # VirtualRunEnv in downstream consumers (e.g., test_package) picks up
        # runenv_info to generate the runtime environment.
        for dep in self.dependencies.values():
            pkg_folder = dep.package_folder
            for libdir in dep.cpp_info.libdirs:
                lib_path = libdir if os.path.isabs(libdir) else os.path.join(pkg_folder, libdir)
                self.runenv_info.append_path("LD_LIBRARY_PATH", lib_path)
