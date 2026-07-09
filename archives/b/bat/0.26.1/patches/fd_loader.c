/* ELF loader for static musl binaries - with AT_PHENT fix */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <signal.h>
#include <sys/mman.h>
#include <sys/wait.h>
#include <elf.h>

#define PAGE_SIZE 4096
#define PAGE_DOWN(x) ((x) & ~(PAGE_SIZE - 1))
#define PAGE_UP(x) (((x) + PAGE_SIZE - 1) & ~(PAGE_SIZE - 1))

struct auxv_entry { unsigned long type, value; };

static char *read_file(const char *path, size_t *size) {
    int fd = open(path, O_RDONLY);
    if (fd < 0) return NULL;
    off_t fsz = lseek(fd, 0, SEEK_END);
    lseek(fd, 0, SEEK_SET);
    char *buf = malloc(fsz);
    if (!buf) { close(fd); return NULL; }
    size_t t = 0;
    while (t < (size_t)fsz) { ssize_t n = read(fd, buf + t, fsz - t); if (n <= 0) break; t += n; }
    close(fd); *size = t; return buf;
}

static void run_elf(const char *elf_path, int argc, char **argv, char **envp) {
    size_t file_size;
    char *elf_data = read_file(elf_path, &file_size);
    if (!elf_data) _exit(1);

    Elf64_Ehdr *ehdr = (Elf64_Ehdr *)elf_data;
    Elf64_Phdr *phdrs = (Elf64_Phdr *)(elf_data + ehdr->e_phoff);
    int phnum = ehdr->e_phnum;
    unsigned long phdr_addr = 0;

    for (int i = 0; i < phnum; i++) {
        Elf64_Phdr *ph = &phdrs[i];
        if (ph->p_type == PT_LOAD) {
            unsigned long addr = PAGE_DOWN(ph->p_vaddr);
            unsigned long seg_end = PAGE_UP(ph->p_vaddr + ph->p_memsz);
            size_t map_sz = seg_end - addr;
            int prot = 0;
            if (ph->p_flags & PF_R) prot |= PROT_READ;
            if (ph->p_flags & PF_W) prot |= PROT_WRITE;
            if (ph->p_flags & PF_X) prot |= PROT_EXEC;
            void *m = mmap((void *)addr, map_sz, PROT_READ|PROT_WRITE,
                           MAP_PRIVATE|MAP_ANONYMOUS|MAP_FIXED, -1, 0);
            if (m == MAP_FAILED) _exit(1);
            if (ph->p_filesz > 0) memcpy((void *)ph->p_vaddr, elf_data+ph->p_offset, ph->p_filesz);
            if (ph->p_memsz > ph->p_filesz) memset((void *)(ph->p_vaddr+ph->p_filesz), 0, ph->p_memsz-ph->p_filesz);
            if (mprotect((void *)addr, map_sz, prot) != 0)
                mprotect((void *)addr, map_sz, PROT_READ|PROT_WRITE|PROT_EXEC);
        }
        if (ph->p_type == PT_PHDR) phdr_addr = ph->p_vaddr;
    }
    if (!phdr_addr)
        for (int i = 0; i < phnum; i++)
            if (phdrs[i].p_type == PT_LOAD) {
                phdr_addr = phdrs[i].p_vaddr + ehdr->e_phoff - phdrs[i].p_offset;
                break;
            }

    int env_count = 0;
    while (envp[env_count]) env_count++;

    size_t stack_sz = 8*1024*1024;
    void *stack = mmap(NULL, stack_sz, PROT_READ|PROT_WRITE, MAP_PRIVATE|MAP_ANONYMOUS, -1, 0);
    if (stack == MAP_FAILED) _exit(1);
    unsigned long sp = (unsigned long)stack + stack_sz;
    sp &= ~15UL;

    char random_bytes[16] = {0};
    int u = open("/dev/urandom", O_RDONLY);
    if (u >= 0) { read(u, random_bytes, 16); close(u); }

    /* auxv entries: AT_PHDR, AT_PHENT, AT_PHNUM, AT_PAGESZ, AT_BASE, AT_ENTRY,
       AT_RANDOM, AT_EXECFN, AT_NULL = 9 entries */
    int auxv_count = 9;
    size_t need = sizeof(unsigned long)+(argc+1)*8+(env_count+1)*8+auxv_count*sizeof(struct auxv_entry)+16+256;
    sp -= need; sp &= ~15UL;
    unsigned long *p = (unsigned long *)sp;
    *p++ = argc;
    for (int i = 0; i < argc; i++) *p++ = (unsigned long)argv[i];
    *p++ = 0;
    for (int i = 0; i < env_count; i++) *p++ = (unsigned long)envp[i];
    *p++ = 0;
    struct auxv_entry *av = (struct auxv_entry *)p;
    int ai = 0;
    av[ai].type=AT_PHDR;  av[ai].value=phdr_addr; ai++;
    av[ai].type=AT_PHENT; av[ai].value=sizeof(Elf64_Phdr); ai++;  /* 56 bytes - THIS WAS MISSING! */
    av[ai].type=AT_PHNUM; av[ai].value=phnum; ai++;
    av[ai].type=AT_PAGESZ; av[ai].value=PAGE_SIZE; ai++;
    av[ai].type=AT_BASE;  av[ai].value=0; ai++;
    av[ai].type=AT_ENTRY; av[ai].value=ehdr->e_entry; ai++;
    char *rand_ptr = (char *)&av[ai];
    memcpy(rand_ptr, random_bytes, 16);
    av[ai].type=AT_RANDOM; av[ai].value=(unsigned long)rand_ptr; ai++;
    av[ai].type=AT_EXECFN; av[ai].value=(unsigned long)elf_path; ai++;
    av[ai].type=AT_NULL;  av[ai].value=0; ai++;

    write(2, "[loader] starting\n", 18);
    unsigned long entry = ehdr->e_entry;
    __asm__ volatile("mov sp, %0\n\tbr %1" : : "r"(sp), "r"(entry) : "memory");
    _exit(0);
}

int main(int argc, char **argv, char **envp) {
    if (argc < 2) { fprintf(stderr, "Usage: %s <elf> [args...]\n", argv[0]); return 1; }
    pid_t pid = fork();
    if (pid == 0) { run_elf(argv[1], argc - 1, &argv[1], envp); _exit(1); }
    int status;
    waitpid(pid, &status, 0);
    if (WIFSIGNALED(status))
        fprintf(stderr, "[parent] signal %d (crash)\n", WTERMSIG(status));
    else if (WIFEXITED(status))
        fprintf(stderr, "[parent] exit %d\n", WEXITSTATUS(status));
    return WIFEXITED(status) ? WEXITSTATUS(status) : 128 + WTERMSIG(status);
}
