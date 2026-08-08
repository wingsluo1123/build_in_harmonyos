#!/usr/bin/env python3
"""Conan recipe for xmlrpc-c — XML-RPC for C/C++.

Build system: custom autotools-like configure + GNUmakefile.
Dependencies: curl (client transport), openssl (abyss-openssl channel).
Bundled: expat (XML parser, built-in).
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class XmlrpcCConan(ConanFile):
    name = "xmlrpc-c"
    version = "1.64.03"
    description = "XML-RPC for C/C++ - programming library for writing XML-RPC clients and servers"
    license = "MIT"
    homepage = "https://sourceforge.net/projects/xmlrpc-c/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
    }
    default_options = {
        "shared": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("curl/8.15.0")
        self.requires("openssl/3.5.6.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

        deps = AutotoolsDeps(self)
        deps.generate()

        # xmlrpc-c's configure uses curl-config to detect curl.
        # Create a wrapper that points to the conan curl package.
        curl_prefix = self.dependencies["curl"].package_folder
        wrapper_dir = os.path.join(self.build_folder, "wrapper_bin")
        os.makedirs(wrapper_dir, exist_ok=True)
        curl_config_path = os.path.join(wrapper_dir, "curl-config")
        with open(curl_config_path, "w") as f:
            f.write(
                "#!/bin/sh\n"
                f'CURL_PREFIX="{curl_prefix}"\n'
                'case "$1" in\n'
                '  --prefix) echo "$CURL_PREFIX" ;;\n'
                '  --cflags) echo "-I$CURL_PREFIX/include" ;;\n'
                '  --libs) echo "-L$CURL_PREFIX/lib -lcurl" ;;\n'
                '  --version) echo "libcurl 8.15.0" ;;\n'
                '  --feature) echo "SSL IPv6 zlib AsynchDNS NTLM threadsafe" ;;\n'
                '  --protocols) echo "DICT FILE FTP FTPS GOPHER HTTP HTTPS IMAP IMAPS MQTT POP3 POP3S RTSP SMB SMTP SMTPS TELNET TFTP" ;;\n'
                '  *) echo "Usage: curl-config [option]" 1>&2; exit 1 ;;\n'
                "esac\n"
            )
        os.chmod(curl_config_path, 0o755)

        # xmlrpc-c's configure uses pkg-config to detect openssl.
        # Create an openssl.pc pointing to the conan openssl package.
        openssl_prefix = self.dependencies["openssl"].package_folder
        pc_dir = os.path.join(self.build_folder, "wrapper_pkgconfig")
        os.makedirs(pc_dir, exist_ok=True)
        with open(os.path.join(pc_dir, "openssl.pc"), "w") as f:
            f.write(
                f"prefix={openssl_prefix}\n"
                "exec_prefix=${prefix}\n"
                "libdir=${prefix}/lib\n"
                "includedir=${prefix}/include\n"
                "\n"
                "Name: OpenSSL\n"
                "Description: SSL/TLS and cryptography library\n"
                "Version: 3.5.6.1\n"
                "Libs: -L${libdir} -lssl -lcrypto\n"
                "Cflags: -I${includedir}\n"
            )

        env = Environment()
        env.prepend_path("PATH", wrapper_dir)
        env.prepend_path("PKG_CONFIG_PATH", pc_dir)
        # Configure test programs link against libcurl.so and libssl.a;
        # set LD_LIBRARY_PATH so they can run at configure time.
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(curl_prefix, "lib"))
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(openssl_prefix, "lib"))
        env.vars(self).save_script("conanbuildenv_xmlrpc_c")

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # xmlrpc-c generates config.h during configure but make install
        # does not copy it to the include directory. Find and copy it.
        for root, dirs, files in os.walk(self.build_folder):
            if "config.h" in files and "xmlrpc-c" in root:
                copy(
                    self,
                    "config.h",
                    src=root,
                    dst=os.path.join(self.package_folder, "include", "xmlrpc-c"),
                )
                break

    def package_info(self):
        self.cpp_info.libs = [
            "xmlrpc",
            "xmlrpc_client",
            "xmlrpc_server",
            "xmlrpc_server_abyss",
            "xmlrpc_server_cgi",
            "xmlrpc_abyss",
            "xmlrpc_openssl",
            "xmlrpc_xmlparse",
            "xmlrpc_xmltok",
            "xmlrpc_util",
            "xmlrpc_cpp",
            "xmlrpc++",
            "xmlrpc_client++",
            "xmlrpc_server++",
            "xmlrpc_server_abyss++",
            "xmlrpc_server_cgi++",
            "xmlrpc_server_pstream++",
            "xmlrpc_packetsocket",
            "xmlrpc_util++",
            "xmlrpc_abyss++",
        ]
        self.cpp_info.requires = ["curl::curl", "openssl::openssl"]
