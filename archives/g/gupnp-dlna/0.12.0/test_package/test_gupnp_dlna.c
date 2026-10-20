/* gupnp-dlna 0.12.0 消费者契约测试（链接 libgupnp-dlna-2.0，真机真实执行）
 *
 * 覆盖：
 *  1) profile-catalog: DLNA profile XML 目录加载 —— guesser 实例化、profile
 *     列表枚举、MP3 profile 存在且 mime=audio/mpeg（GUPnPDLNAProfile API）；
 *  2) relaxed-extended-modes: relaxed/extended 模式 guesser 实例化、模式标志
 *     与 profile 列表；
 *  3) install-layout: GUPNP_DLNA_PROFILE_DIR 下 15 个 profile XML，
 *     GUPNP_DLNA_METADATA_BACKEND_DIR 下 libgstreamer.so 后端模块；
 *     直接解析模块 ELF，校验 .codesign 签名节存在且公开入口
 *     gupnp_dlna_get_default_extractor 在 .dynsym 中导出。
 *
 * 说明（平台边界，如实声明）：本测试不调用 guess_profile_sync() 触发
 * GstDiscoverer，也不 dlopen() 后端模块。OHOS 侧 glib2/gstreamer 只有静态
 * 包，后端模块与 libgupnp-dlna-gst-2.0.so 各自内嵌一份静态 glib，加载即
 * 触发 GType 注册表冲突（设备上隔离进程 dlopen 探针同样 abort：
 * g_type_register_static assertion / SIGABRT）；GStreamer 插件链路的同类
 * 失败已在 gst-plugins-bad1.0 1.28.5 真机实验确认。真实解码链路的设备实测
 * 结论见 0.12.0/notes.md。
 *
 * 本文件刻意只使用 libc + gupnp-dlna 导出符号（不用 g_base64/g_file_utils/
 * g_dir 等 core 未引用的 glib API），避免把静态 glib 成员拉进测试可执行
 * 文件、制造第二份 glib 副本。逐用例输出 TEST PASS/FAIL，末行 TEST SUMMARY；
 * 任一失败 exit(1)。
 */
#include <dirent.h>
#include <elf.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

#include <libgupnp-dlna/gupnp-dlna.h>

static int g_checks;
static int g_fails;

#define CHECK(cond, fmt, ...)                                                \
    do {                                                                     \
        g_checks++;                                                          \
        if (!(cond)) {                                                       \
            g_fails++;                                                       \
            fprintf(stderr, "CHECK FAILED %s:%d: " fmt "\n",                 \
                    __FILE__, __LINE__, ##__VA_ARGS__);                      \
        }                                                                    \
    } while (0)

static void test_end(const char *name, int fails_before)
{
    if (g_fails == fails_before)
        printf("TEST PASS: %s\n", name);
    else
        printf("TEST FAIL: %s\n", name);
}

static int test_profiles(void)
{
    int f0 = g_fails;
    GUPnPDLNAProfileGuesser *guesser;
    GList *profiles;
    GList *item;
    unsigned int count = 0;
    GUPnPDLNAProfile *mp3;
    const gchar *mime = NULL;

    printf("TEST CASE: profile-catalog\n");
    guesser = gupnp_dlna_profile_guesser_new(FALSE, FALSE);
    CHECK(guesser != NULL, "gupnp_dlna_profile_guesser_new returned NULL");
    if (guesser == NULL) {
        test_end("profile-catalog", f0);
        return 1;
    }

    profiles = gupnp_dlna_profile_guesser_list_profiles(guesser);
    CHECK(profiles != NULL, "profile list is NULL");
    for (item = profiles; item != NULL; item = item->next)
        count++;
    CHECK(count >= 60, "profile count %u < 60", count);
    printf("  loaded DLNA profiles: %u\n", count);

    mp3 = gupnp_dlna_profile_guesser_get_profile(guesser, "MP3");
    CHECK(mp3 != NULL, "profile 'MP3' not found");
    if (mp3 != NULL) {
        mime = gupnp_dlna_profile_get_mime(mp3);
        CHECK(mime != NULL && strcmp(mime, "audio/mpeg") == 0,
              "MP3 mime is %s", mime ? mime : "(null)");
    }

    g_object_unref(guesser);
    test_end("profile-catalog", f0);
    return g_fails == f0 ? 0 : 1;
}

static int test_modes(void)
{
    int f0 = g_fails;
    GUPnPDLNAProfileGuesser *guesser;
    GList *profiles;

    printf("TEST CASE: relaxed-extended-modes\n");
    guesser = gupnp_dlna_profile_guesser_new(TRUE, TRUE);
    CHECK(guesser != NULL, "relaxed+extended guesser is NULL");
    if (guesser != NULL) {
        profiles = gupnp_dlna_profile_guesser_list_profiles(guesser);
        CHECK(profiles != NULL, "relaxed+extended profile list is NULL");
        CHECK(gupnp_dlna_profile_guesser_get_relaxed_mode(guesser) == 1,
              "relaxed mode flag lost");
        CHECK(gupnp_dlna_profile_guesser_get_extended_mode(guesser) == 1,
              "extended mode flag lost");
        g_object_unref(guesser);
    }
    test_end("relaxed-extended-modes", f0);
    return g_fails == f0 ? 0 : 1;
}

/* ---- 最小 ELF64 解析：无需 dlopen 即可校验模块签名与导出符号 ---- */

static unsigned char *read_whole_file(const char *path, size_t *size_out)
{
    FILE *f = fopen(path, "rb");
    long size;
    unsigned char *buf;

    if (f == NULL)
        return NULL;
    if (fseek(f, 0, SEEK_END) != 0 || (size = ftell(f)) <= 0) {
        fclose(f);
        return NULL;
    }
    rewind(f);
    buf = malloc((size_t) size);
    if (buf == NULL || fread(buf, 1, (size_t) size, f) != (size_t) size) {
        free(buf);
        fclose(f);
        return NULL;
    }
    fclose(f);
    *size_out = (size_t) size;
    return buf;
}

static const Elf64_Shdr *elf64_sections(const unsigned char *b, size_t n,
                                        const Elf64_Ehdr **eh_out)
{
    const Elf64_Ehdr *eh = (const Elf64_Ehdr *) b;

    if (n < sizeof(*eh) || memcmp(eh->e_ident, ELFMAG, SELFMAG) != 0 ||
        eh->e_ident[EI_CLASS] != ELFCLASS64)
        return NULL;
    if (eh->e_shoff == 0 || eh->e_shnum == 0 || eh->e_shstrndx >= eh->e_shnum)
        return NULL;
    if (eh->e_shentsize != sizeof(Elf64_Shdr))
        return NULL;
    {
        /* subtraction form: off + size can wrap on a corrupt header */
        uint64_t table_size = (uint64_t) eh->e_shnum * eh->e_shentsize;

        if (eh->e_shoff > n || table_size > n - eh->e_shoff)
            return NULL;
    }
    *eh_out = eh;
    return (const Elf64_Shdr *) (b + eh->e_shoff);
}

static int elf64_has_section(const unsigned char *b, size_t n, const char *name)
{
    const Elf64_Ehdr *eh;
    const Elf64_Shdr *sh = elf64_sections(b, n, &eh);
    const Elf64_Shdr *strsh;
    const char *strtab;
    unsigned int i;

    if (sh == NULL)
        return 0;
    strsh = &sh[eh->e_shstrndx];
    if (strsh->sh_offset > n || strsh->sh_size > n - strsh->sh_offset)
        return 0;
    strtab = (const char *) b + strsh->sh_offset;
    for (i = 0; i < eh->e_shnum; i++) {
        if (sh[i].sh_name >= strsh->sh_size)
            continue;
        if (strcmp(strtab + sh[i].sh_name, name) == 0)
            return 1;
    }
    return 0;
}

static int elf64_exports_symbol(const unsigned char *b, size_t n,
                                const char *name)
{
    const Elf64_Ehdr *eh;
    const Elf64_Shdr *sh = elf64_sections(b, n, &eh);
    unsigned int i;

    if (sh == NULL)
        return 0;
    for (i = 0; i < eh->e_shnum; i++) {
        const Elf64_Shdr *symsh = &sh[i];
        const Elf64_Shdr *strsh;
        const Elf64_Sym *syms;
        const char *strtab;
        size_t count, j;

        if (symsh->sh_type != SHT_DYNSYM || symsh->sh_link >= eh->e_shnum)
            continue;
        if (symsh->sh_entsize != sizeof(Elf64_Sym) ||
            symsh->sh_offset > n || symsh->sh_size > n - symsh->sh_offset)
            continue;
        strsh = &sh[symsh->sh_link];
        if (strsh->sh_offset > n || strsh->sh_size > n - strsh->sh_offset)
            continue;
        strtab = (const char *) b + strsh->sh_offset;
        syms = (const Elf64_Sym *) (b + symsh->sh_offset);
        count = symsh->sh_size / symsh->sh_entsize;
        for (j = 0; j < count; j++) {
            if (syms[j].st_name >= strsh->sh_size)
                continue;
            if (strcmp(strtab + syms[j].st_name, name) == 0)
                return 1;
        }
    }
    return 0;
}

static int test_install_layout(void)
{
    int f0 = g_fails;
    const char *profile_dir = getenv("GUPNP_DLNA_PROFILE_DIR");
    const char *backend_dir = getenv("GUPNP_DLNA_METADATA_BACKEND_DIR");
    unsigned int xml_count = 0;
    struct stat st;
    char module[4096];
    unsigned char *blob;
    size_t blob_size = 0;

    printf("TEST CASE: install-layout\n");
    CHECK(profile_dir != NULL && stat(profile_dir, &st) == 0 && S_ISDIR(st.st_mode),
          "GUPNP_DLNA_PROFILE_DIR=%s is not a directory",
          profile_dir ? profile_dir : "(unset)");
    CHECK(backend_dir != NULL && stat(backend_dir, &st) == 0 && S_ISDIR(st.st_mode),
          "GUPNP_DLNA_METADATA_BACKEND_DIR=%s is not a directory",
          backend_dir ? backend_dir : "(unset)");

    if (profile_dir != NULL) {
        DIR *dir = opendir(profile_dir);
        struct dirent *ent;
        CHECK(dir != NULL, "cannot open profile dir %s", profile_dir);
        if (dir != NULL) {
            while ((ent = readdir(dir)) != NULL) {
                size_t len = strlen(ent->d_name);
                if (len > 4 && strcmp(ent->d_name + len - 4, ".xml") == 0)
                    xml_count++;
            }
            closedir(dir);
        }
        CHECK(xml_count >= 15, "profile XML count %u < 15", xml_count);
        printf("  profile XML files: %u\n", xml_count);
    }

    if (backend_dir != NULL) {
        int n = snprintf(module, sizeof(module), "%s/libgstreamer.so", backend_dir);
        CHECK(n > 0 && (size_t) n < sizeof(module),
              "backend module path too long");
        CHECK(stat(module, &st) == 0 && S_ISREG(st.st_mode),
              "backend module missing: %s", module);
        /* 不 dlopen：后端模块与 libgupnp-dlna-gst-2.0.so 各内嵌一份静态
         * glib，加载即触发 GType 注册表冲突（设备隔离探针同样 SIGABRT）。
         * 直接解析 ELF：签名节 .codesign 存在、公开入口符号在 .dynsym
         * 中导出，覆盖安装布局与导出契约。 */
        blob = read_whole_file(module, &blob_size);
        CHECK(blob != NULL, "cannot read backend module %s", module);
        if (blob != NULL) {
            int bf = g_fails;

            CHECK(elf64_has_section(blob, blob_size, ".codesign"),
                  "backend module lacks .codesign signature section");
            CHECK(elf64_exports_symbol(blob, blob_size,
                                       "gupnp_dlna_get_default_extractor"),
                  "backend module does not export the default extractor entry");
            if (g_fails == bf)
                printf("  backend module: ELF64, .codesign present, entry exported\n");
            free(blob);
        }
    }
    test_end("install-layout", f0);
    return g_fails == f0 ? 0 : 1;
}

int main(void)
{
    printf("== gupnp-dlna 0.12.0 consumer API contract test ==\n");

    test_profiles();
    test_modes();
    test_install_layout();

    printf("TEST SUMMARY: %d checks, %d failed -> %s\n",
           g_checks, g_fails,
           g_fails == 0 ? "ALL PASS" : "FAILURES PRESENT");
    return g_fails == 0 ? 0 : 1;
}
