/**
 * riscv64-elf-binutils test package
 * 验证 riscv64-elf 交叉工具链的基本功能。
 *
 * 注意：此测试在主机上运行，验证工具本身可执行（`--version`）。
 * 不需要目标平台（RISC-V）的执行环境。
 */

#include <stdio.h>
#include <stdlib.h>

int main(void) {
    printf("riscv64-elf-binutils test package\n");
    printf("Run 'riscv64-elf-ld --version' etc. via conanfile.py test()\n");
    printf("Tools are expected to print version info when invoked.\n");
    return 0;
}
