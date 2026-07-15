import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, save
from conan.tools.layout import basic_layout


class RedisConan(ConanFile):
    name = "redis"
    version = "8.8.0"
    description = "Redis is an in-memory database that persists on disk"
    license = "RSALv2"
    homepage = "https://redis.io/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"redis only supports Linux/OHOS, got {self.settings.os}"
            )
        env = VirtualBuildEnv(self)
        env.generate()

    def build(self):
        apply_conandata_patches(self)

        # Create pthread cancellation stubs for musl libc (E085)
        # musl/OHOS doesn't implement pthread_cancel, pthread_setcancelstate, etc.
        pthread_compat = (
            "/* OHOS pthread cancellation stubs - musl libc doesn't implement these */\n"
            "#include <pthread.h>\n\n"
            "int pthread_cancel(pthread_t t) { (void)t; return 0; }\n"
            "int pthread_testcancel(void) { return 0; }\n"
            "int pthread_setcancelstate(int s, int *os) { (void)s; if(os) *os = 0; return 0; }\n"
            "int pthread_setcanceltype(int t, int *ot) { (void)t; if(ot) *ot = 0; return 0; }\n"
        )
        save(self, os.path.join(self.source_folder, "src", "pthread_compat.c"), pthread_compat)

        # R33: Get compiler from Conan conf, not from shell env vars.
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")
        self.run(
            f'make CC="{cc}" -j1',
            cwd=self.source_folder,
            env=["conanbuild"],
        )

    def package(self):
        self.run(
            f'make install PREFIX={self.package_folder}',
            cwd=self.source_folder,
            env=["conanbuild"],
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
