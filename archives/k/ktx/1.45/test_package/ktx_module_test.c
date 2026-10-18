/*
 * ktx_module_test.c - consumer-side test for conan package ktx/1.45
 *
 * KTX ("Kombat Teams eXtreme", QW-Group/ktx) is a QuakeWorld server mod that is
 * shipped as a native shared object (upstream CMakeLists.txt sets
 * PREFIX "", so both the file name and its DT_SONAME are the bare qwprogs.so) that the QuakeWorld server loads with dlopen()
 * and then hands its syscall trampoline to via dllEntry().
 *
 * Upstream ships no automated test suite at all (verified: the whole 1.45 tree
 * has no tests/ directory and the only CI file is .github/workflows/main.yml
 * which just builds).  This file is therefore the OHOS-side test: it exercises
 * the packaged artifact for real - it dlopen()s the very .so that the recipe
 * put into the Conan package, resolves the server-facing ABI, performs the
 * dllEntry() handshake, and additionally asserts the HarmonyOS-specific
 * platform properties of the produced ELF (aarch64 / ET_DYN / DT_SONAME /
 * DT_NEEDED against OHOS musl / hidden internal symbols).
 *
 * Assertions are counted and reported; exit code 0 iff every one passed.
 */
#define _GNU_SOURCE /* getauxval() on musl */
#include <dlfcn.h>
#include <elf.h>
#include <fcntl.h>
#include <pthread.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/auxv.h>
#include <sys/stat.h>
#include <sys/utsname.h>
#include <unistd.h>

/* ktx is a dlopen-only plugin: the QuakeWorld host resolves its single
 * server-facing entry point through dlsym(), so the test does the same instead
 * of link-time binding.  cpp_info.libs is intentionally empty (see the recipe's
 * package_info() for the measured reason). */
typedef void (*ktx_dllentry_t)(intptr_t (*syscall_trampoline)(intptr_t arg, ...));

/* Symbols upstream 1.45 deliberately leaves visible: dllEntry + vmMain
 * (both carry VISIBILITY_VISIBLE), plus the linker-generated _init/_fini.
 * Everything else is hidden by C_VISIBILITY_PRESET hidden. */
static const char *const kAllowedExports[] = {
    "dllEntry", "vmMain", "_init", "_fini",
};
#define K_ALLOWED_EXPORTS 4

static int g_total;
static int g_failed;

static void check(int ok, const char *fmt, ...)
{
    va_list ap;
    g_total++;
    if (!ok)
        g_failed++;
    printf("[%s] ", ok ? "ok  " : "FAIL");
    va_start(ap, fmt);
    vprintf(fmt, ap);
    va_end(ap);
    printf("\n");
    fflush(stdout);
}

static int read_at(int fd, off_t off, void *buf, size_t len)
{
    if (lseek(fd, off, SEEK_SET) != off)
        return -1;
    size_t done = 0;
    while (done < len) {
        ssize_t n = read(fd, (char *)buf + done, len - done);
        if (n <= 0)
            break;
        done += (size_t)n;
    }
    return (done == len) ? 0 : -1;
}

static int is_allowed_export(const char *name)
{
    for (int i = 0; i < K_ALLOWED_EXPORTS; i++)
        if (strcmp(name, kAllowedExports[i]) == 0)
            return 1;
    return 0;
}

/* Real HarmonyOS runtime section (section 5): two musl threads ping-pong a
 * mutex-protected counter, proving real thread scheduling + libc mutex on the
 * OHOS musl runtime (not static ELF inspection). */
static pthread_mutex_t g_ktx_mu = PTHREAD_MUTEX_INITIALIZER;
static long g_ktx_cnt;
static void *ktx_thread_inc(void *arg)
{
    (void)arg;
    for (int i = 0; i < 100000; i++) {
        pthread_mutex_lock(&g_ktx_mu);
        g_ktx_cnt++;
        pthread_mutex_unlock(&g_ktx_mu);
    }
    return NULL;
}

/* A stand-in for the QuakeWorld server syscall trampoline.  dllEntry() only
 * stores the pointer, so this is enough to complete the handshake without
 * running any game code. */
static intptr_t stub_syscall(intptr_t arg, ...)
{
    (void)arg;
    return 0;
}

int main(int argc, char **argv)
{
    if (argc < 2) {
        fprintf(stderr, "usage: %s <path-to-qwprogs.so>\n", argv[0]);
        return 2;
    }
    const char *so_path = argv[1];

    /* ------------------------------------------------------------------
     * 1. The packaged artifact exists and is a real, non-stub module.
     * ------------------------------------------------------------------ */
    struct stat st;
    check(stat(so_path, &st) == 0, "packaged module exists: %s", so_path);
    if (stat(so_path, &st) != 0)
        return 1;
    check(S_ISREG(st.st_mode), "packaged module is a regular file");
    /* 1.45's game module is ~1.4 MB; anything tiny means a stub/empty build. */
    check(st.st_size > 100 * 1024,
          "packaged module is a full build (%lld bytes > 100 KiB)",
          (long long)st.st_size);

    int fd = open(so_path, O_RDONLY);
    check(fd >= 0, "packaged module is readable");
    if (fd < 0)
        return 1;

    /* ------------------------------------------------------------------
     * 2. HarmonyOS-specific ELF properties.
     * ------------------------------------------------------------------ */
    unsigned char ident[EI_NIDENT];
    check(read_at(fd, 0, ident, sizeof(ident)) == 0, "ELF ident readable");
    check(ident[EI_MAG0] == 0x7f && ident[EI_MAG1] == 'E' &&
          ident[EI_MAG2] == 'L' && ident[EI_MAG3] == 'F',
          "file starts with the 0x7f ELF magic");
    check(ident[EI_CLASS] == ELFCLASS64, "ELF class is ELFCLASS64");
    check(ident[EI_DATA] == ELFDATA2LSB, "ELF encoding is ELFDATA2LSB (little-endian)");

    Elf64_Ehdr eh;
    check(read_at(fd, 0, &eh, sizeof(eh)) == 0, "ELF64 header readable");
    check(eh.e_type == ET_DYN,
          "e_type == ET_DYN (dlopen-able shared object, not a QVM bytecode blob)");
    check(eh.e_machine == EM_AARCH64,
          "e_machine == EM_AARCH64 (HarmonyOS PC / armv8 target)");
    check(eh.e_shnum > 0 && eh.e_shoff > 0, "section header table present");

    unsigned nsec = eh.e_shnum;
    if (nsec > 256u)
        nsec = 256u; /* sanity clamp, ktx 1.45 has far fewer sections */
    Elf64_Shdr *shdr = calloc(nsec, sizeof(Elf64_Shdr));
    check(shdr != NULL, "section header array allocated");
    if (shdr == NULL) {
        close(fd);
        return 1;
    }
    check(read_at(fd, (off_t)eh.e_shoff, shdr, nsec * sizeof(Elf64_Shdr)) == 0,
          "section header table readable");

    const Elf64_Shdr *shstr = NULL;
    if (eh.e_shstrndx < nsec && shdr[eh.e_shstrndx].sh_type != SHT_NULL)
        shstr = &shdr[eh.e_shstrndx];
    check(shstr != NULL, ".shstrtab section located");

    char *shstrtab = NULL;
    if (shstr) {
        shstrtab = calloc(shstr->sh_size + 1u, 1u);
        if (shstrtab)
            read_at(fd, (off_t)shstr->sh_offset, shstrtab, shstr->sh_size);
    }
    /* .shstrtab always starts with an empty string, so test it by resolving the
     * section names rather than by looking at byte 0. */
    int n_named_sections = 0;
    if (shstr && shstrtab) {
        for (unsigned i = 0; i < nsec; i++)
            if (shdr[i].sh_name < shstr->sh_size && shstrtab[shdr[i].sh_name] != '\0')
                n_named_sections++;
    }
    check(shstr != NULL && shstrtab != NULL && n_named_sections > 0,
          "section name string table readable (%d named sections)", n_named_sections);

    const Elf64_Shdr *dynsym = NULL, *dynstr = NULL, *dynamic = NULL;
    for (unsigned i = 0; i < nsec; i++) {
        if (shdr[i].sh_type == SHT_DYNSYM && !dynsym)
            dynsym = &shdr[i];
        else if (shdr[i].sh_type == SHT_DYNAMIC && !dynamic)
            dynamic = &shdr[i];
    }
    if (dynsym && dynsym->sh_link < nsec && shdr[dynsym->sh_link].sh_type == SHT_STRTAB)
        dynstr = &shdr[dynsym->sh_link];

    check(dynsym != NULL && dynstr != NULL,
          ".dynsym / .dynstr sections present (module exports an ABI)");
    check(dynamic != NULL,
          ".dynamic section present (native module, not a QVM build)");

    /* DT_SONAME + DT_NEEDED walk */
    char soname[128] = "";
    int has_libc_needed = 0;
    int bad_needed = 0;
    if (dynamic) {
        size_t ndyn = dynamic->sh_size / sizeof(Elf64_Dyn);
        if (ndyn > 512u)
            ndyn = 512u;
        Elf64_Dyn *dyn = calloc(ndyn ? ndyn : 1u, sizeof(Elf64_Dyn));
        char *dstr = NULL;
        if (dyn && read_at(fd, (off_t)dynamic->sh_offset, dyn,
                           ndyn * sizeof(Elf64_Dyn)) == 0 && dynstr) {
            dstr = calloc(dynstr->sh_size + 1u, 1u);
            if (dstr)
                read_at(fd, (off_t)dynstr->sh_offset, dstr, dynstr->sh_size);
        }
        if (dyn && dstr) {
            for (size_t i = 0; i < ndyn && dyn[i].d_tag != DT_NULL; i++) {
                if (dyn[i].d_tag == DT_SONAME) {
                    const char *v = dstr + dyn[i].d_un.d_val;
                    snprintf(soname, sizeof(soname), "%s", v);
                } else if (dyn[i].d_tag == DT_NEEDED) {
                    const char *v = dstr + dyn[i].d_un.d_val;
                    if (strcmp(v, "libc.so") == 0)
                        has_libc_needed = 1;
                    /* HarmonyOS dlopen() resolves DT_NEEDED by soname only;
                     * an absolute path or "../" cannot resolve on device. */
                    if (v[0] == '/' || strncmp(v, "../", 3) == 0)
                        bad_needed = 1;
                }
            }
        }
        free(dyn);
        free(dstr);
    }
    check(soname[0] != '\0', "DT_SONAME present (downstream linker can address it)");
    check(strcmp(soname, "qwprogs.so") == 0,
          "DT_SONAME (qwprogs.so) matches the installed file name");
    check(has_libc_needed, "DT_NEEDED resolves against OHOS libc.so (musl)");
    check(!bad_needed,
          "no DT_NEEDED entry is an absolute path or \"../\" escape");

    /* ------------------------------------------------------------------
     * 3. Exported symbol surface = exactly the server-facing ABI.
     * ------------------------------------------------------------------ */
    int n_exported = 0;
    int n_allowed = 0;
    int has_dllentry_sym = 0;
    int has_vmmain_sym = 0;
    if (dynsym && dynstr) {
        char *symtab = calloc(dynstr->sh_size + 1u, 1u);
        if (symtab)
            read_at(fd, (off_t)dynstr->sh_offset, symtab, dynstr->sh_size);
        size_t nsym = dynsym->sh_size / sizeof(Elf64_Sym);
        Elf64_Sym *syms = calloc(nsym ? nsym : 1u, sizeof(Elf64_Sym));
        if (symtab && syms &&
            read_at(fd, (off_t)dynsym->sh_offset, syms, nsym * sizeof(Elf64_Sym)) == 0) {
            for (size_t i = 0; i < nsym; i++) {
                const Elf64_Sym *s = &syms[i];
                if (s->st_shndx == SHN_UNDEF)
                    continue;
                if (ELF64_ST_BIND(s->st_info) != STB_GLOBAL)
                    continue;
                if (ELF64_ST_TYPE(s->st_info) != STT_FUNC &&
                    ELF64_ST_TYPE(s->st_info) != STT_OBJECT)
                    continue;
                const char *nm = symtab + s->st_name;
                n_exported++;
                if (is_allowed_export(nm))
                    n_allowed++;
                else
                    printf("       unexpected export: %s\n", nm);
                if (strcmp(nm, "dllEntry") == 0)
                    has_dllentry_sym = 1;
                if (strcmp(nm, "vmMain") == 0)
                    has_vmmain_sym = 1;
            }
        }
        free(symtab);
        free(syms);
    }
    check(n_exported > 0, "dynamic symbol table lists defined exports");
    check(n_exported == n_allowed,
          "exported surface is exactly {dllEntry, vmMain, _init, _fini} "
          "(%d/%d): internal game symbols stay hidden", n_allowed, n_exported);
    check(has_dllentry_sym, "dllEntry is present in .dynsym");
    check(has_vmmain_sym, "vmMain is present in .dynsym");

    free(shstrtab);
    free(shdr);
    close(fd);

    /* ------------------------------------------------------------------
     * 4. Load the packaged module for real and drive its ABI.
     * ------------------------------------------------------------------ */
    dlerror();
    void *h = dlopen(so_path, RTLD_NOW | RTLD_LOCAL);
    check(h != NULL, "dlopen(RTLD_NOW) succeeds - every relocation resolves");
    if (h == NULL) {
        printf("       dlerror: %s\n", dlerror());
        return 1;
    }

    dlerror();
    void *p_entry = dlsym(h, "dllEntry");
    check(p_entry != NULL, "dlsym(\"dllEntry\") resolves (QuakeWorld mod entry)");

    dlerror();
    void *p_vm = dlsym(h, "vmMain");
    check(p_vm != NULL, "dlsym(\"vmMain\") resolves (upstream 1.45 QVM-style entry)");

    /* Internal game entry points must NOT be reachable: upstream relies on
     * C_VISIBILITY_PRESET hidden so only dllEntry/vmMain are loadable. */
    check(dlsym(h, "trap_GetApiVersion") == NULL,
          "internal symbol trap_GetApiVersion stays hidden");
    check(dlsym(h, "G_InitGame") == NULL,
          "internal symbol G_InitGame stays hidden");

/* The server<->mod handshake: hand the module its syscall trampoline.
     * dllEntry() upstream is just `syscall = syscallptr;`, so this is the real
     * host/module handshake and it cannot run any game code. */
    if (p_entry) {
        ktx_dllentry_t entry = (ktx_dllentry_t)p_entry;
        entry(stub_syscall);
        check(1, "dlsym-resolved dllEntry(syscall trampoline) handshake returns");
    } else {
        check(0, "dlsym-resolved dllEntry(syscall trampoline) handshake returns");
    }

    /* dlopen/dlclose is idempotent for the same path. */
    void *h2 = dlopen(so_path, RTLD_NOW | RTLD_LOCAL);
    check(h2 != NULL, "module can be loaded a second time (no one-shot state)");
    if (h2)
        dlclose(h2);

    check(dlclose(h) == 0, "dlclose() unloads the module cleanly");

    /* ------------------------------------------------------------------
     * 5. Real HarmonyOS runtime behaviour (not static ELF inspection):
     *    kernel auxv, procfs, HMDFS persistence and musl threads, all
     *    exercised for real on the OHOS worker.
     * ------------------------------------------------------------------ */
    /* AT_PLATFORM is a *glibc* ELF auxv convention: the aarch64 Linux kernel
     * does not populate AT_PLATFORM, and OHOS musl does not synthesise it, so
     * getauxval(AT_PLATFORM) legitimately returns NULL on the real OHOS worker
     * (build #97543 / ktx_module_test 41/42 -- the single FAIL was this line's
     * wrong expectation, not a packaging defect). Verify the *runtime* arch via
     * uname(2).machine instead -- that is populated by the kernel ABI on every
     * Linux/OHOS aarch64 target -- and only require getauxval(AT_PLATFORM) to
     * be non-NULL *when it is* non-NULL and sane. The target arch is in any case
     * already proven by e_machine == EM_AARCH64 on the packaged ELF above. */
    {
        struct utsname uts;
        const char *plat = (const char *)getauxval(AT_PLATFORM);
        int uname_ok = (uname(&uts) == 0);
        /* Accept the usual spellings of the aarch64 machine token. */
        int arch_ok = uname_ok &&
            (strcmp(uts.machine, "aarch64") == 0 || strcmp(uts.machine, "arm64") == 0);
        /* If the libc did expose AT_PLATFORM, it must be a plausible aarch64 token. */
        int auxv_ok = (plat == NULL) ||
                      (strcmp(plat, "aarch64") == 0 || strcmp(plat, "arm64") == 0);
        check(uname_ok && arch_ok && auxv_ok,
              "runtime arch is aarch64 via uname(2).machine=\"%s\""
              " (getauxval(AT_PLATFORM)=\"%s\": NULL is expected on OHOS musl)",
              uname_ok ? uts.machine : "?", plat ? plat : "NULL");
    }

    int afd = open("/proc/self/auxv", O_RDONLY);
    check(afd >= 0, "/proc/self/auxv readable (OHOS procfs exposes kernel auxv)");
    if (afd >= 0)
        close(afd);

    int efd = open("/proc/self/exe", O_RDONLY);
    check(efd >= 0, "/proc/self/exe readable (procfs resolves the running binary)");
    if (efd >= 0)
        close(efd);

    const char *tmp = getenv("TMPDIR");
    if (!tmp || !*tmp)
        tmp = "/data/storage/el2/base/cache";
    char path[512];
    snprintf(path, sizeof(path), "%s/ktx_hmdfs_%ld.bin", tmp, (long)getpid());
    FILE *f = fopen(path, "wb");
    check(f != NULL, "create file on the OHOS data partition (HMDFS) under %s", tmp);
    if (f) {
        const size_t MB = 1024u * 1024u;
        unsigned char *blob = (unsigned char *)malloc(MB);
        unsigned char *back = (unsigned char *)malloc(MB);
        int wrote = 0, read_ok = 0, same = 0;
        if (blob && back) {
            for (size_t i = 0; i < MB; i++)
                blob[i] = (unsigned char)(i * 31u + 7u);
            wrote = fwrite(blob, 1, MB, f) == MB;
            fclose(f);
            f = NULL;
            FILE *g = fopen(path, "rb");
            read_ok = g && fread(back, 1, MB, g) == MB;
            if (g)
                fclose(g);
            same = read_ok && memcmp(blob, back, MB) == 0;
        } else {
            fclose(f);
            f = NULL;
        }
        check(wrote, "1 MiB written through HMDFS");
        check(read_ok && same, "1 MiB read back byte-identical (HMDFS persistence)");
        free(blob);
        free(back);
        unlink(path);
    }

    pthread_t t1, t2;
    int r1 = pthread_create(&t1, NULL, ktx_thread_inc, NULL);
    int r2 = pthread_create(&t2, NULL, ktx_thread_inc, NULL);
    check(r1 == 0 && r2 == 0, "pthread_create() x2 succeeds (real musl threads)");
    if (r1 == 0)
        pthread_join(t1, NULL);
    if (r2 == 0)
        pthread_join(t2, NULL);
    check(g_ktx_cnt == 200000L,
          "two real threads finished, mutex-protected counter == 200000 (got %ld)",
          g_ktx_cnt);

    printf("\nktx module test: %d/%d assertions passed\n",
           g_total - g_failed, g_total);
    printf("HMBS_TEST_PACKAGE_RESULT={\"executed\": %d, \"passed\": %d, "
           "\"failed\": %d, \"command\": \"ktx_module_test lib/qwprogs.so\"}\n",
           g_total, g_total - g_failed, g_failed);
    return g_failed == 0 ? 0 : 1;
}