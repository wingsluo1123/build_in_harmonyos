"""Conan recipe for percona-server 8.0.36 - Percona Server for MySQL client library.

Builds only the client library (libperconaserverclient), not the full database server.
Used by qt-percona-server as the MySQL protocol backend.

Build system: CMake
Produces: libperconaserverclient.so (and .a)

Dependencies: openssl, zlib; Boost headers are fetched from upstream archives
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, copy, replace_in_file, rm


class PerconaServerConan(ConanFile):
    name = "percona-server"
    version = "8.0.36"
    description = "Percona Server for MySQL client library (libperconaserverclient)"
    license = "GPL-2.0-only"
    homepage = "https://www.percona.com/"
    url = ""  # CI fills this

    package_type = "library"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    settings = "os", "arch", "compiler", "build_type"

    exports_sources = "conandata.yml"

    def requirements(self):
        self.requires("openssl/3.5.6")
        self.requires("zlib/1.3.1")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        get(self, **self.conan_data["boost"],
            destination=os.path.join(self.source_folder, "boost"), strip_root=True)
        replace_in_file(
            self,
            os.path.join(self.source_folder, "CMakeLists.txt"),
            r'''IF(EDITLINE_WARN_GIVEN)
  MESSAGE(FATAL_ERROR
    "-DWITH_EDITLINE=system, but missing system libraries.\n"
    "You can use -DWITH_EDITLINE=bundled instead."
    )
ENDIF()''',
            r'''IF(EDITLINE_WARN_GIVEN AND NOT WITHOUT_SERVER)
  MESSAGE(FATAL_ERROR
    "-DWITH_EDITLINE=system, but missing system libraries.\n"
    "You can use -DWITH_EDITLINE=bundled instead."
    )
ELSEIF(EDITLINE_WARN_GIVEN)
  MESSAGE(WARNING
    "-DWITH_EDITLINE=system, but missing system libraries; "
    "continuing because WITHOUT_SERVER=ON builds only client libraries."
    )
ENDIF()''',
        )
        replace_in_file(
            self,
            os.path.join(self.source_folder, "libmysql", "CMakeLists.txt"),
            'MESSAGE(FATAL_ERROR "Can\'t find neither Win32 nor Unix DNS SRV APIs")',
            'MESSAGE(WARNING "Can\'t find neither Win32 nor Unix DNS SRV APIs; mysql_real_connect_dns_srv will return an unsupported error")',
        )
        replace_in_file(
            self,
            os.path.join(self.source_folder, "libmysql", "dns_srv.cc"),
            '''#error "No DNS SRV Support detected for your OS. Consider adjusting Cmake."

#if 0
// dummy function returning an error in case it's not supported by the OS

static bool get_dns_srv(Dns_srv_data &data, const char *dnsname, int &error) {
  error = -1;  // set a special error code for not supported
  return true;
}
#endif''',
            '''// Dummy function returning an error in case DNS SRV is not supported by the OS.
static bool get_dns_srv(Dns_srv_data &data, const char *dnsname, int &error) {
  error = -1;  // set a special error code for not supported
  return true;
}''',
        )
        replace_in_file(
            self,
            os.path.join(self.source_folder, "mysys", "my_thread.cc"),
            '''int my_thread_cancel(my_thread_handle *thread) {
#ifndef _WIN32
  return pthread_cancel(thread->thread);
#else''',
            '''#ifndef HAVE_PTHREAD_CANCEL
#define HAVE_PTHREAD_CANCEL 0
#endif

int my_thread_cancel(my_thread_handle *thread) {
#if !defined(_WIN32) && HAVE_PTHREAD_CANCEL
  return pthread_cancel(thread->thread);
#elif !defined(_WIN32)
  (void)thread;
  return 0;
#else''',
        )
        replace_in_file(
            self,
            os.path.join(self.source_folder, "sql-common", "get_password.cc"),
            '''    char tmp;
    if (my_read(fd, &tmp, 1, MYF(0)) != 1) break;''',
            '''    uchar tmp;
    if (my_read(fd, &tmp, 1, MYF(0)) != 1) break;''',
        )


    def generate(self):
        tc = CMakeToolchain(self)
        # Build client library only, not the full server
        tc.variables["WITHOUT_SERVER"] = "ON"
        # Use Conan-provided OpenSSL and zlib, set explicit paths
        tc.variables["WITH_SSL"] = "system"
        tc.variables["OPENSSL_ROOT_DIR"] = self.dependencies["openssl"].package_folder
        tc.variables["WITH_ZLIB"] = "system"
        tc.variables["ZLIB_ROOT"] = self.dependencies["zlib"].package_folder
        # Provide the Boost version expected by Percona/MySQL 8.0.36 without
        # declaring an unpublished Conan Boost dependency or relying on CMake's
        # JFrog download URL, which can return a non-archive response.
        tc.variables["DOWNLOAD_BOOST"] = "0"
        tc.variables["WITH_BOOST"] = os.path.join(self.source_folder, "boost")
        # Disable optional server authentication plugins that require LDAP/SASL/Kerberos.
        tc.variables["WITH_AUTHENTICATION_LDAP"] = "OFF"
        tc.variables["WITHOUT_COMPONENT_KEYRING_KMIP"] = "ON"
        # Do not use the default WITH_READLINE=system path, which fails hard if
        # curses/readline are unavailable. The source() adjustment makes missing
        # system editline non-fatal for the client-only build.
        tc.variables["WITH_EDITLINE"] = "system"
        # pthread_cancel is unavailable on some libc implementations; the
        # source adjustment uses a feature macro instead of a platform macro.
        # ARM64 specific: use -fPIC for shared library compatibility
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = "ON"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        # Build only the client library target, not the whole server. Use -j1
        # because OHOS storage does not allow make jobserver FIFOs.
        cmake.build(target="perconaserverclient", build_tool_args=["-j1"])

    def package(self):
        # Install source headers (top-level include/)
        copy(self, "*.h", dst=os.path.join(self.package_folder, "include"),
             src=os.path.join(self.source_folder, "include"))
        # Install build-generated headers (my_config.h, mysql_version.h etc.)
        copy(self, "*.h", dst=os.path.join(self.package_folder, "include"),
             src=os.path.join(self.build_folder, "include"))
        # Install client library (MySQL builds into libmysql/ subdirectory)
        copy(self, "*perconaserverclient*", dst=os.path.join(self.package_folder, "lib"),
             src=self.build_folder, keep_path=False)
        copy(self, "*mysqlclient*", dst=os.path.join(self.package_folder, "lib"),
             src=self.build_folder, keep_path=False)
        # Clean up unwanted files
        for pattern in ["*.la", "*.dylib"]:
            rm(self, pattern, folder=os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["perconaserverclient"]
        self.cpp_info.includedirs = ["include"]
        # Propagate dependencies to consumers (e.g. qt-percona-server)
        self.cpp_info.requires = ["openssl::openssl", "zlib::zlib"]