#!/usr/bin/env python3
"""Conan recipe — boolector 3.2.4 (SMT solver).

Btor2Tools dependency replaced with stub (external source unavailable).
PicoSAT built from source as the SAT solver backend.
"""
import os

from conan import ConanFile
from conan.tools.files import get, save, load, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class BoolectorConan(ConanFile):
    name = "boolector"
    version = "3.2.4"
    description = "Boolector SMT Solver (BTOR2 stub + bundled PicoSAT)"
    license = "MIT"
    homepage = "https://boolector.github.io"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        # Download boolector source
        get(self, **self.conan_data["sources"]["boolector"], strip_root=True)
        # Download PicoSAT source
        get(self, **self.conan_data["sources"]["picosat"], strip_root=True,
            destination=os.path.join(self.source_folder, "picosat"))

        # Create btor2parser stub header
        stub_h = r'''#ifndef btor2parser_h_INCLUDED
#define btor2parser_h_INCLUDED
#include <stdint.h>
#include <stdio.h>
#if __cplusplus
extern "C" {
#endif
#define BTOR2_FORMAT_MAXID (((int64_t) 1) << 40)
#define BTOR2_FORMAT_MAXBITWIDTH ((1l << 30) + ((1l << 30) - 1))
typedef struct Btor2Parser Btor2Parser;
typedef struct Btor2Line Btor2Line;
typedef struct Btor2Sort Btor2Sort;
typedef struct Btor2LineIterator Btor2LineIterator;
enum Btor2Tag
{
  BTOR2_TAG_add, BTOR2_TAG_and, BTOR2_TAG_bad, BTOR2_TAG_concat,
  BTOR2_TAG_const, BTOR2_TAG_constraint, BTOR2_TAG_constd, BTOR2_TAG_consth,
  BTOR2_TAG_dec, BTOR2_TAG_eq, BTOR2_TAG_fair, BTOR2_TAG_iff,
  BTOR2_TAG_implies, BTOR2_TAG_inc, BTOR2_TAG_init, BTOR2_TAG_input,
  BTOR2_TAG_ite, BTOR2_TAG_justice, BTOR2_TAG_mul, BTOR2_TAG_nand,
  BTOR2_TAG_neq, BTOR2_TAG_neg, BTOR2_TAG_next, BTOR2_TAG_nor,
  BTOR2_TAG_not, BTOR2_TAG_one, BTOR2_TAG_ones, BTOR2_TAG_or,
  BTOR2_TAG_output, BTOR2_TAG_read, BTOR2_TAG_redand, BTOR2_TAG_redor,
  BTOR2_TAG_redxor, BTOR2_TAG_rol, BTOR2_TAG_ror, BTOR2_TAG_saddo,
  BTOR2_TAG_sdiv, BTOR2_TAG_sdivo, BTOR2_TAG_sext, BTOR2_TAG_sgt,
  BTOR2_TAG_sgte, BTOR2_TAG_slice, BTOR2_TAG_sll, BTOR2_TAG_slt,
  BTOR2_TAG_slte, BTOR2_TAG_sort, BTOR2_TAG_smod, BTOR2_TAG_smulo,
  BTOR2_TAG_sra, BTOR2_TAG_srem, BTOR2_TAG_srl, BTOR2_TAG_ssubo,
  BTOR2_TAG_state, BTOR2_TAG_sub, BTOR2_TAG_uaddo, BTOR2_TAG_udiv,
  BTOR2_TAG_uext, BTOR2_TAG_ugt, BTOR2_TAG_ugte, BTOR2_TAG_ult,
  BTOR2_TAG_ulte, BTOR2_TAG_umulo, BTOR2_TAG_urem, BTOR2_TAG_usubo,
  BTOR2_TAG_write, BTOR2_TAG_xnor, BTOR2_TAG_xor, BTOR2_TAG_zero,
};
typedef enum Btor2Tag Btor2Tag;
enum Btor2SortTag
{
  BTOR2_TAG_SORT_array,
  BTOR2_TAG_SORT_bitvec,
};
typedef enum Btor2SortTag Btor2SortTag;
struct Btor2Sort
{
  int64_t id;
  Btor2SortTag tag;
  const char *name;
  union { struct { int64_t index; int64_t element; } array; struct { uint32_t width; } bitvec; };
};
struct Btor2Line
{
  int64_t id;
  int64_t lineno;
  const char *name;
  Btor2Tag tag;
  Btor2Sort sort;
  int64_t init, next;
  char *constant;
  char *symbol;
  uint32_t nargs;
  int64_t *args;
};
struct Btor2LineIterator
{
  Btor2Parser *reader;
  int64_t next;
};
Btor2Parser *btor2parser_new (void);
void btor2parser_delete (Btor2Parser *);
int32_t btor2parser_read_lines (Btor2Parser *, FILE *);
const char *btor2parser_error (Btor2Parser *);
Btor2LineIterator btor2parser_iter_init (Btor2Parser *bfr);
Btor2Line *btor2parser_iter_next (Btor2LineIterator *);
int64_t btor2parser_max_id (Btor2Parser *);
Btor2Line *btor2parser_get_line_by_id (Btor2Parser *, int64_t id);
#if __cplusplus
}
#endif
#endif
'''
        save(self, os.path.join(self.source_folder, "btor2parser.h"), stub_h)

        # Create btor2parser stub implementation
        stub_c = r'''#include "btor2parser.h"
#include <stdlib.h>
struct Btor2Parser { int dummy; };
static const char *stub_error = "BTOR2 parser not available (btor2tools stub)";
Btor2Parser *btor2parser_new (void) { return calloc(1, sizeof(Btor2Parser)); }
void btor2parser_delete (Btor2Parser *p) { free(p); }
int32_t btor2parser_read_lines (Btor2Parser *p, FILE *f) { (void)p; (void)f; return 0; }
const char *btor2parser_error (Btor2Parser *p) { (void)p; return stub_error; }
Btor2LineIterator btor2parser_iter_init (Btor2Parser *bfr) { Btor2LineIterator it; it.reader = bfr; it.next = 0; return it; }
Btor2Line *btor2parser_iter_next (Btor2LineIterator *it) { (void)it; return 0; }
int64_t btor2parser_max_id (Btor2Parser *p) { (void)p; return 0; }
Btor2Line *btor2parser_get_line_by_id (Btor2Parser *p, int64_t id) { (void)p; (void)id; return 0; }
'''
        save(self, os.path.join(self.source_folder, "btor2parser.c"), stub_c)

        # Patch main CMakeLists.txt:
        # Replace find_package(Btor2Tools REQUIRED) with local include/dir only
        cmakefile = load(self, os.path.join(self.source_folder, "CMakeLists.txt"))
        cmakefile = cmakefile.replace(
            "find_package(Btor2Tools REQUIRED)",
            "set(Btor2Tools_INCLUDE_DIR \"${CMAKE_SOURCE_DIR}\")\n"
            "set(Btor2Tools_LIBRARIES \"\")\n"
            "set(Btor2Tools_FOUND TRUE)"
        )
        # Replace PicoSAT find_package with local include/dir
        cmakefile = cmakefile.replace(
            "find_package(PicoSAT)",
            "set(PicoSAT_INCLUDE_DIR \"${CMAKE_SOURCE_DIR}/picosat\")\n"
            "set(PicoSAT_LIBRARIES \"\")\n"
            "set(PicoSAT_FOUND TRUE)"
        )
        save(self, os.path.join(self.source_folder, "CMakeLists.txt"), cmakefile)

        # Patch src/CMakeLists.txt: add stub and picosat sources directly to
        # the boolector library to avoid separate targets in export set
        srccmake = load(self, os.path.join(self.source_folder, "src", "CMakeLists.txt"))
        # Add btor2parser.c, picosat.c and version.c to the source list
        srccmake = srccmake.replace(
            "  utils/btorutil.c\n)",
            "  utils/btorutil.c\n"
            "  ../btor2parser.c\n"
            "  ../picosat/picosat.c\n"
            "  ../picosat/version.c\n)"
        )
        # Remove the Btor2Tools_LIBRARIES link (sources are now in the target)
        srccmake = srccmake.replace(
            "target_include_directories(boolector PRIVATE ${Btor2Tools_INCLUDE_DIR})\n"
            "target_link_libraries(boolector ${Btor2Tools_LIBRARIES})",
            "target_include_directories(boolector PRIVATE ${Btor2Tools_INCLUDE_DIR})"
        )
        # Remove PicoSAT_LIBRARIES link (sources are now in the target)
        srccmake = srccmake.replace(
            "  target_link_libraries(boolector ${PicoSAT_LIBRARIES})",
            ""
        )
        # Fix btormc: remove Btor2Tools_LIBRARIES link
        srccmake = srccmake.replace(
            "target_link_libraries(btormc boolector ${Btor2Tools_LIBRARIES})",
            "target_link_libraries(btormc boolector)"
        )
        # Disable btorimc (uses typeof in C++ which clang doesn't support)
        srccmake = srccmake.replace(
            "add_executable (btorimc ${btorimc_src_files})",
            "# add_executable (btorimc ${btorimc_src_files})  # disabled: typeof in C++"
        )
        srccmake = srccmake.replace(
            "target_link_libraries(btorimc boolector)",
            "# target_link_libraries(btorimc boolector)"
        )
        # Remove btorimc from static targets and install
        srccmake = srccmake.replace(
            "set(STATIC_TARGETS boolector-bin btormc btoruntrace btorimc)",
            "set(STATIC_TARGETS boolector-bin btormc btoruntrace)"
        )
        srccmake = srccmake.replace(
            "install(TARGETS btorimc DESTINATION bin)",
            "# install(TARGETS btorimc DESTINATION bin)"
        )
        save(self, os.path.join(self.source_folder, "src", "CMakeLists.txt"), srccmake)

        # Patch picosat.c: sys/unistd.h not available on OHOS, use unistd.h
        picosat_c_path = os.path.join(self.source_folder, "picosat", "picosat.c")
        picosat_c = load(self, picosat_c_path)
        picosat_c = picosat_c.replace("#include <sys/unistd.h>", "#include <unistd.h>")
        save(self, picosat_c_path, picosat_c)

        # Create standalone version.c (original needs config.h from configure.sh)
        version_c = '''#include "picosat.h"
const char *picosat_version (void) { return "965"; }
const char *picosat_config (void) { return "clang -O2"; }
'''
        save(self, os.path.join(self.source_folder, "picosat", "version.c"), version_c)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.variables["TESTING"] = "OFF"
        tc.variables["USE_MINISAT"] = "OFF"
        tc.variables["USE_CMS"] = "OFF"
        tc.variables["USE_LINGELING"] = "OFF"
        tc.variables["USE_CADICAL"] = "OFF"
        # PicoSAT will be found via the patched CMakeLists.txt
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["boolector"]
