/*
 * 打开上游自带的「运行时探测、缺失则回退 C 实现」开关。
 * AES-CE / PMULL 由默认的 MBEDTLS_AESCE_C 编译进来；
 * SHA-256 与 SHA-512 的 Armv8 加密扩展在 3.6 默认配置里是注释掉的。
 * 这里只定义 *_IF_PRESENT，不定义 *_ONLY，因此没有指令的机器会走软件路径。
 * 不使用平台条件宏。非 Arm 目标上上游会自行忽略这些开关。
 */
#define MBEDTLS_SHA256_USE_ARMV8_A_CRYPTO_IF_PRESENT
#define MBEDTLS_SHA512_USE_A64_CRYPTO_IF_PRESENT
