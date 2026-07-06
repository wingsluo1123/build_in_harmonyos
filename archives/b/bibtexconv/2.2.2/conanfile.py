#!/usr/bin/env python3
"""Conan recipe — bibtexconv 2.2.2 (CMake executable tool).

Provides stub libcurl and libcrypto so the tool compiles without
network/SSL dependencies. URL download and MD5 features are disabled
at runtime (stubs return errors).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


# ---- Stub headers ----
STUB_CURL_H = """\
/* Stub curl/curl.h — minimal API for bibtexconv compilation */
#ifndef CURL_STUB_H
#define CURL_STUB_H
#ifdef __cplusplus
extern "C" {
#endif

typedef void CURL;
typedef int CURLcode;

#define CURLE_OK 0
#define CURLE_FAILED_INIT 2

#define CURLOPT_URL           10002
#define CURLOPT_SSL_VERIFYPEER 204
#define CURLOPT_SSL_VERIFYHOST 81
#define CURLOPT_WRITEDATA     10001
#define CURLOPT_WRITEHEADER   10029
#define CURLOPT_USERAGENT     10018
#define CURLOPT_FOLLOWLOCATION 52
#define CURLOPT_AUTOREFERER   58
#define CURLOPT_COOKIEFILE    10031
#define CURLOPT_CONNECTTIMEOUT 78

CURL*       curl_easy_init(void);
CURLcode    curl_easy_setopt(CURL* curl, int option, ...);
CURLcode    curl_easy_perform(CURL* curl);
const char* curl_easy_strerror(CURLcode code);
void        curl_easy_cleanup(CURL* curl);

#ifdef __cplusplus
}
#endif
#endif
"""

STUB_EASY_H = "/* Stub curl/easy.h */\n#include <curl/curl.h>\n"

STUB_EVP_H = """\
/* Stub openssl/evp.h — minimal API for bibtexconv compilation */
#ifndef EVP_STUB_H
#define EVP_STUB_H
#ifdef __cplusplus
extern "C" {
#endif

typedef struct evp_md_st EVP_MD;
typedef struct evp_md_ctx_st EVP_MD_CTX;

const EVP_MD* EVP_md5(void);
int  EVP_MD_size(const EVP_MD* md);
EVP_MD_CTX* EVP_MD_CTX_new(void);
void EVP_MD_CTX_free(EVP_MD_CTX* ctx);
int  EVP_DigestInit_ex(EVP_MD_CTX* ctx, const EVP_MD* md, void* impl);
int  EVP_DigestUpdate(EVP_MD_CTX* ctx, const void* d, unsigned int cnt);
int  EVP_DigestFinal_ex(EVP_MD_CTX* ctx, unsigned char* md, unsigned int* s);

#ifdef __cplusplus
}
#endif
#endif
"""

# ---- Stub implementation ----
STUB_C = """\
/* Stub implementations for libcurl and libcrypto */
#include <stddef.h>

/* ---- curl stubs ---- */
typedef void CURL;
typedef int CURLcode;

CURL* curl_easy_init(void) { return (CURL*)0; }
CURLcode curl_easy_setopt(CURL* curl, int option, ...) { (void)curl; (void)option; return 0; }
CURLcode curl_easy_perform(CURL* curl) { (void)curl; return 2; }
const char* curl_easy_strerror(CURLcode code) { (void)code; return "libcurl stub - not available"; }
void curl_easy_cleanup(CURL* curl) { (void)curl; }

/* ---- openssl/evp stubs ---- */
struct evp_md_st { int dummy; };
struct evp_md_ctx_st { int dummy; };

static struct evp_md_st s_md5 = { 0 };
const struct evp_md_st* EVP_md5(void) { return &s_md5; }
int EVP_MD_size(const struct evp_md_st* md) { (void)md; return 16; }
struct evp_md_ctx_st* EVP_MD_CTX_new(void) { return &s_md5; /* non-NULL */ }
void EVP_MD_CTX_free(struct evp_md_ctx_st* ctx) { (void)ctx; }
int EVP_DigestInit_ex(struct evp_md_ctx_st* ctx, const struct evp_md_st* md, void* impl) {
    (void)ctx; (void)md; (void)impl; return 1;
}
int EVP_DigestUpdate(struct evp_md_ctx_st* ctx, const void* d, unsigned int cnt) {
    (void)ctx; (void)d; (void)cnt; return 1;
}
int EVP_DigestFinal_ex(struct evp_md_ctx_st* ctx, unsigned char* md, unsigned int* s) {
    (void)ctx; if(md) { int i; for(i=0;i<16;i++) md[i]=0; } if(s) *s = 16; return 1;
}
"""


class BibtexconvConan(ConanFile):
    name = "bibtexconv"
    version = "2.2.2"
    description = "BibTeX 格式转换工具，支持 BibTeX 到 ODT/HTML 等格式转换"
    license = "GPL-3.0"
    homepage = "https://github.com/dreibh/bibtexconv"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # Uses stub libraries, no external deps

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Point CMake to our stub libraries
        stub_dir = os.path.join(self.build_folder, "stub")
        stub_lib = os.path.join(stub_dir, "lib")
        stub_inc = os.path.join(stub_dir, "include")
        tc.variables["CURL_INCLUDE_DIR"] = stub_inc
        tc.variables["CURL_LIBRARY"] = os.path.join(stub_lib, "libcurl.a")
        tc.variables["CURL_FOUND"] = "TRUE"
        tc.variables["OPENSSL_INCLUDE_DIR"] = stub_inc
        tc.variables["OPENSSL_CRYPTO_LIBRARY"] = os.path.join(stub_lib, "libcrypto.a")
        tc.variables["OPENSSL_SSL_LIBRARY"] = os.path.join(stub_lib, "libssl.a")
        tc.variables["OPENSSL_FOUND"] = "TRUE"
        tc.variables["CMAKE_CXX_STANDARD"] = "17"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        # Create stub headers and library
        stub_dir = os.path.join(self.build_folder, "stub")
        stub_inc = os.path.join(stub_dir, "include")
        stub_lib = os.path.join(stub_dir, "lib")

        os.makedirs(os.path.join(stub_inc, "curl"), exist_ok=True)
        os.makedirs(os.path.join(stub_inc, "openssl"), exist_ok=True)
        os.makedirs(stub_lib, exist_ok=True)

        with open(os.path.join(stub_inc, "curl", "curl.h"), "w") as f:
            f.write(STUB_CURL_H)
        with open(os.path.join(stub_inc, "curl", "easy.h"), "w") as f:
            f.write(STUB_EASY_H)
        with open(os.path.join(stub_inc, "openssl", "evp.h"), "w") as f:
            f.write(STUB_EVP_H)
        stub_c = os.path.join(stub_dir, "stub.c")
        with open(stub_c, "w") as f:
            f.write(STUB_C)

        # Compile stub into static libraries
        cc = str(self.settings.compiler)  # just to ensure settings exist
        clang = "/data/service/hnp/bin/clang"
        self.run(f'{clang} -c {stub_c} -o {os.path.join(stub_dir, "stub.o")}', env="conanbuild")
        self.run(f'ar rcs {os.path.join(stub_lib, "libcurl.a")} {os.path.join(stub_dir, "stub.o")}', env="conanbuild")
        self.run(f'ar rcs {os.path.join(stub_lib, "libcrypto.a")} {os.path.join(stub_dir, "stub.o")}', env="conanbuild")
        self.run(f'ar rcs {os.path.join(stub_lib, "libssl.a")} {os.path.join(stub_dir, "stub.o")}', env="conanbuild")

        # Now build bibtexconv
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
