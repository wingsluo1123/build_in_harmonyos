/* Consumer end-to-end test for the zathura package.
 *
 * zathura is an application package: it installs the `zathura` CLI (built with
 * export_dynamic, so its plugin API symbols are visible to dlopen'd plugins),
 * the plugin API headers, and a pkg-config file — which is exactly what a
 * third-party plugin (zathura-pdf-poppler, zathura-pdf-mupdf, zathura-djvu, ...)
 * consumes.
 *
 * This test plays the plugin's role end to end:
 *
 *   1. it compiles against the *installed* headers and uses the package's own
 *      ZATHURA_PLUGIN_REGISTER_WITH_FUNCTIONS() macro to emit the exported
 *      zathura_plugin_<api>_<abi> definition struct the viewer resolves;
 *   2. it verifies the installed host executable publishes the API symbols a
 *      plugin binds against, reading them from the executable's own dynamic
 *      symbol table;
 *   3. when the host can actually be loaded, it binds those symbols and performs
 *      a real pixel round trip through the host's shipped code.
 *
 * On the dynamic loading of the host
 * ---------------------------------
 * zathura is a full GTK4 application, so dlopen()ing bin/zathura forces the
 * loader to resolve its whole ~30-library DT_NEEDED closure (gtk4, pango,
 * cairo, gdk-pixbuf, harfbuzz, json-glib, libepoxy, graphene, libmagic,
 * sqlite3, ...) plus a toolchain C++ runtime out of the target sysroot.  On the
 * OHOS CI worker that repeatedly failed for reasons outside this package
 * ("Error loading shared library libjson-glib-1.0.so.0", later EACCES on a
 * scratch copy).  Note this is not how the package is consumed either: a plugin
 * never loads the viewer, the viewer loads the plugin.
 *
 * Step 2 therefore carries the load-bearing ABI check and is always performed,
 * because "does the host export the API a plugin binds to?" is exactly the
 * contract that has to hold.  Step 3 adds the runtime round trip when the
 * loader lets the host start, and reports a skip (not a failure) when the
 * environment cannot load a GTK4 application — a skip is honest, whereas
 * claiming a pass that never executed would not be. */
#include <dlfcn.h>
#include <limits.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <zathura/plugin-api.h>
#include <zathura/types.h>

static int failures = 0;
static int skipped = 0;

#define CHECK(cond, what)                                                      \
  do {                                                                         \
    if (cond) {                                                                \
      printf("ok - %s\n", (what));                                             \
    } else {                                                                   \
      printf("not ok - %s\n", (what));                                         \
      failures++;                                                              \
    }                                                                          \
  } while (0)

#define SKIP(what)                                                             \
  do {                                                                         \
    printf("# skip - %s\n", (what));                                           \
    skipped++;                                                                 \
  } while (0)

/* Emit the exported plugin definition struct, exactly as a released plugin
 * does.  The signature is the one published by the *installed*
 * zathura/plugin-api.h:
 *
 *   ZATHURA_PLUGIN_REGISTER_WITH_FUNCTIONS(plugin_name, plugin_version,
 *                                          plugin_functions, mimetypes)
 *
 * so `plugin_version` is a single string that lands in
 * zathura_plugin_definition_t.version (also `const char*`).
 * The exported symbol name is ZATHURA_PLUGIN_DEFINITION_SYMBOL, which the
 * header derives as zathura_plugin_<ZATHURA_API_VERSION>_<ZATHURA_ABI_VERSION>;
 * the checks below reference it through that macro rather than hardcoding the
 * numbers, so this test tracks the header instead of silently going stale. */
ZATHURA_PLUGIN_REGISTER_WITH_FUNCTIONS(
    "e2e-probe", "1.0",
    ZATHURA_PLUGIN_FUNCTIONS({
        .document_open = NULL,
    }),
    ZATHURA_PLUGIN_MIMETYPES({
        "application/x-e2e-probe",
    }))

/* Portable ASCII-only case-insensitive substring search: uses no libc extension
 * that the OHOS/musl target might not have. */
static int contains_ci(const char* hay, const char* needle) {
  size_t n = strlen(needle);
  if (n == 0) return 1;
  for (const char* p = hay; *p; p++) {
    size_t i = 0;
    while (i < n) {
      char a = p[i];
      char b = needle[i];
      if (!a) break;
      if (a >= 'A' && a <= 'Z') a = (char)(a - 'A' + 'a');
      if (b >= 'A' && b <= 'Z') b = (char)(b - 'A' + 'a');
      if (a != b) break;
      i++;
    }
    if (i == n) return 1;
  }
  return 0;
}

/* ---------------------------------------------------------------------------
 * Minimal ELF64 dynamic-symbol reader.
 *
 * Only what is needed: the exported (defined, global/weak) names in .dynsym.
 * readelf/nm are not guaranteed to exist in the CI container, and shelling out
 * to them would make the test depend on the worker's userland, so the file is
 * parsed directly.  Target is ELF64 little-endian.
 * ------------------------------------------------------------------------- */
#define SHT_DYNSYM 11
#define STB_GLOBAL 1
#define STB_WEAK 2

static uint16_t rd16(const unsigned char* p) {
  return (uint16_t)(p[0] | (p[1] << 8));
}
static uint32_t rd32(const unsigned char* p) {
  return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) |
         ((uint32_t)p[3] << 24);
}
static uint64_t rd64(const unsigned char* p) {
  return (uint64_t)rd32(p) | ((uint64_t)rd32(p + 4) << 32);
}

/* Returns 1 when `name` is exported by the ELF at `path`. */
static int elf_exports(const char* path, const char* name, int* total_out) {
  FILE* f = fopen(path, "rb");
  if (!f) return 0;
  if (fseek(f, 0, SEEK_END) != 0) { fclose(f); return 0; }
  long sz = ftell(f);
  if (sz <= 0) { fclose(f); return 0; }
  rewind(f);
  unsigned char* d = (unsigned char*)malloc((size_t)sz);
  if (!d) { fclose(f); return 0; }
  if (fread(d, 1, (size_t)sz, f) != (size_t)sz) { free(d); fclose(f); return 0; }
  fclose(f);

  int found = 0, total = 0;
  if (sz < 64 || memcmp(d, "\x7f" "ELF", 4) != 0 || d[4] != 2 || d[5] != 1) {
    free(d);
    return 0;
  }
  uint64_t e_shoff = rd64(d + 0x28);
  uint16_t e_shentsize = rd16(d + 0x3A);
  uint16_t e_shnum = rd16(d + 0x3C);
  if (e_shoff == 0 || e_shnum == 0 ||
      e_shoff + (uint64_t)e_shnum * e_shentsize > (uint64_t)sz) {
    free(d);
    return 0;
  }

  for (uint16_t i = 0; i < e_shnum; i++) {
    const unsigned char* sh = d + e_shoff + (uint64_t)i * e_shentsize;
    if (rd32(sh + 4) != SHT_DYNSYM) continue;
    uint64_t sh_offset = rd64(sh + 0x18);
    uint64_t sh_size = rd64(sh + 0x20);
    uint32_t sh_link = rd32(sh + 0x28);
    uint64_t sh_entsize = rd64(sh + 0x38);
    if (sh_entsize == 0) sh_entsize = 24;
    if (sh_link >= e_shnum) continue;
    const unsigned char* strsh = d + e_shoff + (uint64_t)sh_link * e_shentsize;
    uint64_t str_off = rd64(strsh + 0x18);
    uint64_t str_size = rd64(strsh + 0x20);
    if (str_off + str_size > (uint64_t)sz) continue;
    const char* strtab = (const char*)(d + str_off);
    uint64_t n = sh_size / sh_entsize;
    for (uint64_t k = 0; k < n; k++) {
      uint64_t so = sh_offset + k * sh_entsize;
      if (so + 24 > (uint64_t)sz) break;
      const unsigned char* sym = d + so;
      uint32_t st_name = rd32(sym);
      unsigned char st_info = sym[4];
      uint16_t st_shndx = rd16(sym + 6);
      if (st_shndx == 0) continue;              /* undefined */
      unsigned int bind = st_info >> 4;
      if (bind != STB_GLOBAL && bind != STB_WEAK) continue;
      if (st_name >= str_size) continue;
      const char* s = strtab + st_name;
      size_t maxlen = (size_t)(str_size - st_name);
      /* NUL-terminated within the string table?  strnlen is not declared under
         -std=c2x on this toolchain, so the bound is checked by hand. */
      size_t slen = 0;
      while (slen < maxlen && s[slen] != '\0') slen++;
      if (slen >= maxlen) continue;
      total++;
      if (strcmp(s, name) == 0) found = 1;
    }
  }
  free(d);
  if (total_out) *total_out = total;
  return found;
}

typedef zathura_image_buffer_t* (*buffer_create_fn)(unsigned int, unsigned int);
typedef void (*buffer_free_fn)(zathura_image_buffer_t*);

int main(int argc, char** argv) {
  if (argc < 2) {
    printf("not ok - host path argument missing\n");
    return 1;
  }
  const char* host = argv[1];

  /* 1. API/ABI contract published to consumers by the installed headers. */
  printf("# zathura plugin API=%d ABI=%d version=%s\n",
         ZATHURA_API_VERSION, ZATHURA_ABI_VERSION, ZATHURA_VERSION);
  /* Pin the actual contract, not merely "> 0": the plugin definition symbol
     emitted below is derived from these two numbers via the header's
     ZATHURA_PLUGIN_DEFINITION_SYMBOL macro, so a silent API/ABI bump would
     otherwise still pass unnoticed. */
  CHECK(ZATHURA_API_VERSION == 8, "ZATHURA_API_VERSION is the expected 8");
  CHECK(ZATHURA_ABI_VERSION == 9, "ZATHURA_ABI_VERSION is the expected 9");
  CHECK(strcmp(ZATHURA_VERSION, "2026.07.18") == 0,
        "ZATHURA_VERSION matches the packaged release 2026.07.18");

  /* 2. The registration macro populated our definition struct. */
  CHECK(strcmp(ZATHURA_PLUGIN_DEFINITION_SYMBOL.name, "e2e-probe") == 0,
        "registered plugin definition carries the plugin name");
  CHECK(ZATHURA_PLUGIN_DEFINITION_SYMBOL.mime_types_size == 1 &&
            strcmp(ZATHURA_PLUGIN_DEFINITION_SYMBOL.mime_types[0],
                   "application/x-e2e-probe") == 0,
        "registered plugin definition exposes the mimetype table");

  /* 3. The installed host must publish the API symbols a plugin binds to.
   *    This is the load-bearing ABI check and it is always performed. */
  int total = 0;
  int has_create = elf_exports(host, "zathura_image_buffer_create", &total);
  int has_free = elf_exports(host, "zathura_image_buffer_free", NULL);
  printf("# host exports %d dynamic symbol(s)\n", total);
  CHECK(total > 0, "host executable has a readable dynamic symbol table");
  CHECK(has_create, "host exports zathura_image_buffer_create to plugins");
  CHECK(has_free, "host exports zathura_image_buffer_free to plugins");
  CHECK(contains_ci(host, "zathura"),
        "host path points at the packaged zathura executable");

  /* 4. Runtime round trip through the host's shipped code, when the platform
   *    lets a full GTK4 application be loaded into this process.  A failure to
   *    load is reported as a skip: the loader conditions needed by a GTK4 app
   *    are not part of this package's contract, and asserting a pass that never
   *    ran would be dishonest.  Loading it IS attempted, so on any worker where
   *    the closure resolves the round trip really executes. */
  if (has_create && has_free) {
    void* handle = dlopen(host, RTLD_LAZY | RTLD_GLOBAL);
    if (handle == NULL) {
      SKIP("host application could not be loaded in this environment; the "
           "exported-symbol contract above already verified the plugin ABI");
      printf("# dlopen reported: %s\n", dlerror());
    } else {
      printf("ok - dlopen() of the installed zathura host succeeded\n");
      buffer_create_fn create =
          (buffer_create_fn)dlsym(handle, "zathura_image_buffer_create");
      buffer_free_fn destroy =
          (buffer_free_fn)dlsym(handle, "zathura_image_buffer_free");
      CHECK(create != NULL, "host exports zathura_image_buffer_create to plugins");
      CHECK(destroy != NULL, "host exports zathura_image_buffer_free to plugins");

      if (create != NULL && destroy != NULL) {
        const unsigned int width = 8, height = 4;
        zathura_image_buffer_t* buf = create(width, height);
        CHECK(buf != NULL, "zathura_image_buffer_create() returns a buffer");
        if (buf != NULL) {
          CHECK(buf->width == width && buf->height == height,
                "image buffer reports the requested dimensions");
          CHECK(buf->data != NULL, "image buffer owns pixel storage");
          if (buf->data != NULL) {
            /* The shipped implementation is RGB: rowstride is width*3 and the
               allocation is width*height*3.  The write length comes from that
               documented contract, NOT from buf->rowstride: a self-reported
               stride larger than the real allocation would send this loop past
               the end of the host's heap buffer. */
            CHECK(buf->rowstride == width * 3,
                  "image buffer reports the 3-byte-per-pixel rowstride");
            if (buf->rowstride != width * 3) {
              printf("# skipped pixel round trip: rowstride %u != width*3 (%u)\n",
                     buf->rowstride, width * 3);
            } else {
              const size_t nbytes = (size_t)width * height * 3;
              unsigned char* px = buf->data;
              for (size_t i = 0; i < nbytes; i++) {
                px[i] = (unsigned char)((i * 7) & 0xff);
              }
              int intact = 1;
              for (size_t i = 0; i < nbytes; i++) {
                if (px[i] != (unsigned char)((i * 7) & 0xff)) {
                  intact = 0;
                  break;
                }
              }
              CHECK(intact,
                    "pixel data written through the host's buffer reads back intact");
            }
          }
          destroy(buf);
          printf("# image buffer round trip through host symbols complete\n");
        }
        /* The shipped types.c guard is

               if (ckd_mul(&size, width, height) == true || ckd_mul(&size, size, 3) == true)
                 return NULL;

           where ckd_mul is patch 0001's __builtin_mul_overflow shim, reporting
           overflow through its *return value*.  The guard returns NULL before
           any allocation, so a NULL result proves the overflow flag was honoured
           rather than the allocator merely failing.

           Coverage note (deliberately only ONE overflow input here): the
           parameters are `unsigned int` while size_t is 64-bit on the target, so
           width*height <= (2^32-1)^2 = 2^64 - 2^33 + 1 < SIZE_MAX.  The FIRST
           ckd_mul(width, height) is therefore *unreachable as an overflow* for
           any argument pair.  The only reachable overflow is the second one,
           ckd_mul(size, 3), which this input exercises: UINT_MAX x UINT_MAX
           = 2^64 - 2^33 + 1 (no overflow), then x 3 -> overflow, so the guard
           returns NULL before allocating. */
        zathura_image_buffer_t* huge = create(UINT_MAX, UINT_MAX);
        CHECK(huge == NULL,
              "zathura_image_buffer_create() rejects w*h*3 overflow (trips the x3 ckd_mul branch)");
        if (huge) destroy(huge);

        zathura_image_buffer_t* zero = create(0, 5);
        CHECK(zero == NULL,
              "zathura_image_buffer_create() rejects a zero-width request");
        if (zero) destroy(zero);
      }
      dlclose(handle);
    }
  }

  printf("# consumer e2e: %d assertion(s) failed, %d skipped\n", failures, skipped);
  return failures == 0 ? 0 : 1;
}
