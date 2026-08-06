/* scooter 0.9.1 test_package — 验证 scooter 二进制存在 + ELF header（arm64 OHOS）。
 *
 * scooter 是 Rust 应用（cargo build 产出单二进制），无 C 库可链接。
 * 本文件满足 L0c 门禁（test_package 必须有 test 源文件），
 * 运行时验证在 conanfile.py test() 中通过 self.run() 完成。
 */
#include <stdio.h>
#include <string.h>

int main(void) {
    printf("scooter test_package: source file present (L0c gate)\n");
    /* 真实验证逻辑在 test_package/conanfile.py test()：
     * 交叉编译场景校验 ELF magic 0x7f 'E' 'L' 'F'，原生场景跑 --version/--help */
    return 0;
}
