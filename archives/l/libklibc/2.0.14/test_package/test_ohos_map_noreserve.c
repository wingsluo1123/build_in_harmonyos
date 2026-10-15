#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <sys/mman.h>

#ifndef MAP_NORESERVE
#define MAP_NORESERVE 0x4000
#endif

int main(void)
{
	size_t size = (size_t)0x100000001ULL;
	volatile unsigned char *p;

	p = mmap(NULL, size, PROT_READ | PROT_WRITE,
		 MAP_PRIVATE | MAP_ANONYMOUS | MAP_NORESERVE, -1, 0);
	if (p == MAP_FAILED) {
		perror("mmap MAP_NORESERVE 4 GiB + 1");
		return 1;
	}
	p[size - 1] = 0x5a;
	if (p[size - 1] != 0x5a) {
		fprintf(stderr, "last-page write/read mismatch\n");
		return 2;
	}
	if (munmap((void *)p, size) != 0) {
		perror("munmap");
		return 3;
	}
	puts("MAP_NORESERVE large sparse mapping: PASS");
	return 0;
}
