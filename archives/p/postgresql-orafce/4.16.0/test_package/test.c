#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <elf.h>

/* Verify orafce.so is a valid ELF shared library by reading its header.
 * We cannot dlopen it because orafce.so has undefined symbols (PostgreSQL
 * server functions) that are only resolved when loaded by the PostgreSQL
 * server process. Instead, we verify the binary format and structure. */
int main(int argc, char *argv[]) {
    if (argc < 2) {
        fprintf(stderr, "Usage: %s <path_to_orafce.so>\n", argv[0]);
        return 1;
    }

    int fd = open(argv[1], O_RDONLY);
    if (fd < 0) {
        fprintf(stderr, "Cannot open %s: %s\n", argv[1], strerror(errno));
        return 1;
    }

    struct stat st;
    if (fstat(fd, &st) < 0) {
        fprintf(stderr, "fstat failed\n");
        close(fd);
        return 1;
    }

    void *map = mmap(NULL, st.st_size, PROT_READ, MAP_PRIVATE, fd, 0);
    if (map == MAP_FAILED) {
        fprintf(stderr, "mmap failed\n");
        close(fd);
        return 1;
    }

    Elf64_Ehdr *ehdr = (Elf64_Ehdr *)map;

    /* Check ELF magic */
    if (memcmp(ehdr->e_ident, ELFMAG, SELFMAG) != 0) {
        fprintf(stderr, "Not an ELF file\n");
        munmap(map, st.st_size);
        close(fd);
        return 1;
    }

    /* Check it's a 64-bit ELF */
    if (ehdr->e_ident[EI_CLASS] != ELFCLASS64) {
        fprintf(stderr, "Not a 64-bit ELF\n");
        munmap(map, st.st_size);
        close(fd);
        return 1;
    }

    /* Check it's a shared library (ET_DYN) */
    if (ehdr->e_type != ET_DYN) {
        fprintf(stderr, "Not a shared library (e_type=%d)\n", ehdr->e_type);
        munmap(map, st.st_size);
        close(fd);
        return 1;
    }

    /* Check machine type is AArch64 */
    if (ehdr->e_machine != EM_AARCH64) {
        fprintf(stderr, "Not AArch64 (e_machine=%d)\n", ehdr->e_machine);
        munmap(map, st.st_size);
        close(fd);
        return 1;
    }

    /* Check for program headers (shared library must have them) */
    if (ehdr->e_phnum == 0) {
        fprintf(stderr, "No program headers\n");
        munmap(map, st.st_size);
        close(fd);
        return 1;
    }

    /* Check for section headers (for symbol table) */
    if (ehdr->e_shnum == 0) {
        fprintf(stderr, "No section headers\n");
        munmap(map, st.st_size);
        close(fd);
        return 1;
    }

    printf("orafce.so verified: valid 64-bit AArch64 ELF shared library\n");
    munmap(map, st.st_size);
    close(fd);
    return 0;
}
