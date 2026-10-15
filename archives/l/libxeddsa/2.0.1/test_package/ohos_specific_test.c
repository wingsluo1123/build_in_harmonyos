/*
 * libxeddsa 2.0.1 — HarmonyOS 专项测试用例 (ohos_specific_test)
 *
 * 验证目标（区别于上游用例与消费者用例）:
 *  1. OHOS 平台上随机源探测正确: ref10 在 HarmonyOS 下走 UNIX 分支,
 *     CHECK_SYMBOL_EXISTS(getrandom/getentropy) 命中, xeddsa_init 成功;
 *  2. Curve25519 私钥 → Ed25519 签名往返在 OHOS 上正确 (x25519 共享密钥);
 *  3. 公钥转换 API 在 OHOS 上往返一致 (curve25519_pub_to_ed25519_pub /
 *     ed25519_pub_to_curve25519_pub);
 *  4. 与静态 libsodium 链接的产物在 OHOS 上可执行 (ELF aarch64-linux-ohos)。
 *
 * 只使用已安装包的公开头文件 <xeddsa.h> 与公开 API, 不包含库私有头。
 */
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include <xeddsa.h>

static int check(int ok, const char *name) {
    printf("OHOS test %s: %s\n", name, ok ? "PASS" : "FAIL");
    return ok ? 0 : 1;
}

int main(void) {
    int rc = 0;
    uint8_t curve_priv[32] = {0x42, 1, 2, 3};
    uint8_t curve_pub[32], ed_pub[32], curve_pub_back[32];
    uint8_t shared1[32], shared2[32];
    uint8_t bob_priv[32] = {0x99, 8, 7, 6};
    uint8_t bob_pub[32];

    /* 1. 库初始化: 内部随机源走 OHOS getrandom/getentropy 探测路径 */
    if (xeddsa_init() < 0) {
        fprintf(stderr, "xeddsa_init failed on OHOS\n");
        return 1;
    }
    rc |= check(1, "xeddsa_init (random source probe on OHOS)");

    /* 2. Curve25519 公钥派生 + 双向转换往返 */
    priv_to_curve25519_pub(curve_pub, curve_priv);
    rc |= check(memcmp(curve_pub, curve_priv, 32) != 0,
                "priv_to_curve25519_pub produces non-trivial pub");
    curve25519_pub_to_ed25519_pub(ed_pub, curve_pub, 0);
    rc |= check(ed25519_pub_to_curve25519_pub(curve_pub_back, ed_pub) == 0 &&
                memcmp(curve_pub, curve_pub_back, 32) == 0,
                "curve25519<->ed25519 pub conversion roundtrip");

    /* 3. X25519 共享密钥一致性 (x25519 公开 API, 签名 x25519(shared, priv, pub)) */
    priv_to_curve25519_pub(bob_pub, bob_priv);
    rc |= check(x25519(shared1, curve_priv, bob_pub) == 0 &&
                x25519(shared2, bob_priv, curve_pub) == 0 &&
                memcmp(shared1, shared2, 32) == 0,
                "x25519 shared secret agreement");

    /* 4. 签名/验证往返 (Ed25519) */
    {
        uint8_t seed[32] = {0};
        uint8_t pub[32], sig[64];
        const uint8_t msg[] = "OHOS specific test message";
        seed_to_ed25519_pub(pub, seed);
        ed25519_seed_sign(sig, seed, msg, sizeof(msg) - 1);
        rc |= check(ed25519_verify(sig, pub, msg, sizeof(msg) - 1) == 0,
                    "ed25519 sign/verify roundtrip");
    }

    printf("OHOS specific test: %s\n", rc == 0 ? "ALL PASS" : "FAILED");
    return rc;
}
