/* test_wayland_info_ohos.c — wayland-utils 1.2.0 层 3 鸿蒙特有测试
 *
 * 仅 OHOS 编译（#ifndef __OHOS__ #error 守卫）。对安装出的 bin/wayland-info
 * 做 ELF 级断言：
 *
 * 平台属性（12 项）：
 *   - valid ELF magic / ELF64 / little-endian / AArch64 machine
 *   - PIE executable (ET_DYN) / dynamically linked (PT_INTERP present)
 *   - non-executable stack (NX) / RELRO present（OHOS 安全基线）
 *   - links libwayland-client.so.0 与 libc.so（解析出的 Conan 依赖链
 *     真实嵌入产物）
 *   - DT_RUNPATH 指向 wayland 包 libdir（裸跑冒烟的关键：OHOS 无
 *     ld.so.conf 指向 conan 缓存，主配方用 patchelf 嵌入）
 *
 * 协议接口数据符号（19 项）：.symtab 内 19 个 wl_interface 数据符号
 * （5 组协议的全部接口）已定义且为 STT_OBJECT —— 证明上游
 * wayland-info/meson.build 的 generated_protocols 字典生成的 5 组协议
 * 绑定真实编译链接进了产物。
 *
 * Assertion count: 31. Exit code 0 iff all pass.
 */
#ifndef __OHOS__
#error "test_wayland_info_ohos.c must be compiled for HarmonyOS (OHOS)"
#endif

#include <elf.h>
#include <errno.h>
#include <fcntl.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>

/* 19 个接口数据符号：上游 generated_protocols 字典 5 组协议的全部接口
 * （wayland-protocols 1.48 安装集 XML 实测接口清单） */
static const char *k_iface_symbols[] = {
    /* presentation-time */
    "wp_presentation_interface",
    "wp_presentation_feedback_interface",
    /* drm-lease-v1 */
    "wp_drm_lease_device_v1_interface",
    "wp_drm_lease_connector_v1_interface",
    "wp_drm_lease_request_v1_interface",
    "wp_drm_lease_v1_interface",
    /* linux-dmabuf-unstable-v1 */
    "zwp_linux_dmabuf_v1_interface",
    "zwp_linux_buffer_params_v1_interface",
    "zwp_linux_dmabuf_feedback_v1_interface",
    /* tablet-unstable-v2 */
    "zwp_tablet_manager_v2_interface",
    "zwp_tablet_seat_v2_interface",
    "zwp_tablet_tool_v2_interface",
    "zwp_tablet_v2_interface",
    "zwp_tablet_pad_ring_v2_interface",
    "zwp_tablet_pad_strip_v2_interface",
    "zwp_tablet_pad_group_v2_interface",
    "zwp_tablet_pad_v2_interface",
    /* xdg-output-unstable-v1 */
    "zxdg_output_manager_v1_interface",
    "zxdg_output_v1_interface",
};

static int g_pass = 0;
static int g_fail = 0;

static void check(int cond, const char *name)
{
    if (cond) {
        g_pass++;
        printf("  [ok]   %s\n", name);
    } else {
        g_fail++;
        printf("  [FAIL] %s\n", name);
    }
}

int main(int argc, char **argv)
{
    if (argc < 3) {
        fprintf(stderr, "usage: %s <installed-wayland-info> "
                        "<wayland-package-libdir>\n", argv[0]);
        return 2;
    }
    const char *path = argv[1];
    const char *want_runpath = argv[2];

    int fd = open(path, O_RDONLY);
    if (fd < 0) {
        fprintf(stderr, "cannot open %s: %s\n", path, strerror(errno));
        return 2;
    }
    struct stat st;
    if (fstat(fd, &st) != 0) {
        perror("fstat");
        close(fd);
        return 2;
    }
    void *map = mmap(NULL, (size_t)st.st_size, PROT_READ, MAP_PRIVATE, fd, 0);
    if (map == MAP_FAILED) {
        perror("mmap");
        close(fd);
        return 2;
    }
    close(fd);

    const unsigned char *bytes = (const unsigned char *)map;
    const Elf64_Ehdr *eh = (const Elf64_Ehdr *)bytes;

    /* ── ELF 头部 ── */
    check(st.st_size >= (off_t)sizeof(Elf64_Ehdr), "ELF header fits in file");
    check(eh->e_ident[EI_MAG0] == ELFMAG0 && eh->e_ident[EI_MAG1] == ELFMAG1 &&
              eh->e_ident[EI_MAG2] == ELFMAG2 && eh->e_ident[EI_MAG3] == ELFMAG3,
          "valid ELF magic");
    check(eh->e_ident[EI_CLASS] == ELFCLASS64, "ELF64 class");
    check(eh->e_ident[EI_DATA] == ELFDATA2LSB, "little-endian (ELFDATA2LSB)");
    check(eh->e_machine == EM_AARCH64, "AArch64 machine (EM_AARCH64)");
    check(eh->e_type == ET_DYN, "PIE executable (ET_DYN)");

    /* ── 程序头：INTERP / NX / RELRO ── */
    int has_interp = 0, has_stack = 0, stack_nx = 0, has_relro = 0;
    for (int i = 0; i < eh->e_phnum; i++) {
        const Elf64_Phdr *ph =
            (const Elf64_Phdr *)(bytes + eh->e_phoff +
                                 (size_t)i * eh->e_phentsize);
        if (ph->p_type == PT_INTERP)
            has_interp = 1;
        if (ph->p_type == PT_GNU_STACK) {
            has_stack = 1;
            stack_nx = (ph->p_flags & PF_X) == 0;
        }
        if (ph->p_type == PT_GNU_RELRO)
            has_relro = 1;
    }
    check(has_interp, "dynamically linked (PT_INTERP present)");
    check(has_stack && stack_nx, "non-executable stack (NX)");
    check(has_relro, "RELRO (PT_GNU_RELRO present)");

    /* ── 动态段：DT_NEEDED / DT_RUNPATH ── */
    int needs_wayland = 0, needs_libc = 0;
    char runpath[4096] = "";
    for (int i = 0; i < eh->e_phnum; i++) {
        const Elf64_Phdr *ph =
            (const Elf64_Phdr *)(bytes + eh->e_phoff +
                                 (size_t)i * eh->e_phentsize);
        if (ph->p_type != PT_DYNAMIC)
            continue;
        /* 先取 DT_STRTAB（虚拟地址），经程序头换算文件偏移 */
        const Elf64_Dyn *dyn = (const Elf64_Dyn *)(bytes + ph->p_offset);
        Elf64_Addr strtab_va = 0;
        for (; dyn->d_tag != DT_NULL; dyn++) {
            if (dyn->d_tag == DT_STRTAB) {
                strtab_va = dyn->d_un.d_ptr;
                break;
            }
        }
        if (strtab_va == 0)
            continue;
        const char *strtab = NULL;
        for (int j = 0; j < eh->e_phnum; j++) {
            const Elf64_Phdr *pj =
                (const Elf64_Phdr *)(bytes + eh->e_phoff +
                                     (size_t)j * eh->e_phentsize);
            if (pj->p_type == PT_LOAD &&
                strtab_va >= pj->p_vaddr &&
                strtab_va < pj->p_vaddr + pj->p_filesz) {
                strtab = (const char *)(bytes + pj->p_offset +
                                        (strtab_va - pj->p_vaddr));
                break;
            }
        }
        if (strtab == NULL)
            continue;
        dyn = (const Elf64_Dyn *)(bytes + ph->p_offset);
        for (; dyn->d_tag != DT_NULL; dyn++) {
            if (dyn->d_tag == DT_NEEDED || dyn->d_tag == DT_RUNPATH ||
                dyn->d_tag == DT_RPATH) {
                const char *nm = strtab + dyn->d_un.d_val;
                if (dyn->d_tag == DT_NEEDED) {
                    if (strcmp(nm, "libwayland-client.so.0") == 0)
                        needs_wayland = 1;
                    if (strcmp(nm, "libc.so") == 0)
                        needs_libc = 1;
                } else {
                    snprintf(runpath, sizeof runpath, "%s", nm);
                }
            }
        }
    }
    check(needs_wayland,
          "links libwayland-client.so.0 (Conan dependency chain)");
    check(needs_libc, "links libc.so");
    check(want_runpath[0] && strstr(runpath, want_runpath) != NULL,
          "DT_RUNPATH points at wayland package libdir (bare-run capable)");

    /* ── .symtab：19 个协议接口数据符号 ── */
    int syms_found = 0;
    const char *dynstr_base = NULL;
    const Elf64_Sym *symtab = NULL;
    size_t symcount = 0;
    {
        const Elf64_Shdr *sh = (const Elf64_Shdr *)(bytes + eh->e_shoff);
        int symtab_idx = -1, strtab_idx = -1;
        for (int i = 0; i < eh->e_shnum; i++) {
            if (sh[i].sh_type == SHT_SYMTAB) {
                symtab_idx = i;
                strtab_idx = (int)sh[i].sh_link;
                break;
            }
        }
        if (symtab_idx >= 0 && strtab_idx >= 0) {
            symtab = (const Elf64_Sym *)(bytes + sh[symtab_idx].sh_offset);
            symcount = sh[symtab_idx].sh_size / sizeof(Elf64_Sym);
            dynstr_base = (const char *)(bytes + sh[strtab_idx].sh_offset);
        }
    }
    for (size_t k = 0;
         k < sizeof k_iface_symbols / sizeof k_iface_symbols[0]; k++) {
        int found = 0;
        if (symtab && dynstr_base) {
            for (size_t i = 0; i < symcount; i++) {
                if (symtab[i].st_name == 0)
                    continue;
                const char *nm = dynstr_base + symtab[i].st_name;
                if (strcmp(nm, k_iface_symbols[k]) == 0 &&
                    symtab[i].st_shndx != SHN_UNDEF &&
                    ELF64_ST_TYPE(symtab[i].st_info) == STT_OBJECT) {
                    found = 1;
                    break;
                }
            }
        }
        check(found, k_iface_symbols[k]);
        if (found)
            syms_found++;
    }

    printf("wayland-utils OHOS-specific consumer test: %d passed, %d failed "
           "(symbols %d/19)\n", g_pass, g_fail, syms_found);
    munmap(map, (size_t)st.st_size);
    return g_fail == 0 ? 0 : 1;
}
