// 端到端消费者用例（非纯断言）：模拟 Qt5 消费者（psi 谱系）在鸿蒙 PC 上
// 通过 qca-qt5 完成一条真实业务流程——凭据指纹与传输编码管线：
//   1) 生成随机会话盐（QCA::Random）
//   2) 对"盐+口令"做 SHA-256 摘要（防彩虹表加盐指纹）
//   3) 摘要走 Base64 传输编码 → 解码 → 与原摘要逐字节比对（回环验证）
//   4) 二次独立计算同指纹，验证可重现性；换盐必须得到不同指纹
// 任何一步失败即非零退出，全部跑通才算消费者流程通过。
// 算法选择说明：本包 BUILD_PLUGINS=ossl，sha256/random/tls 由 qca-ossl
// 插件提供（sha1/md5/base64 来自 base 内置 provider）。摘要选 sha256 而非
// sha1 是刻意的：它让消费者流程真实穿过插件路径，即 psi 实际依赖的能力域。
// 文件尾部另有鸿蒙（__OHOS__）专有断言，见下方注释。
#include <qca.h>
#include <QtCore/QByteArray>
#include <cstdio>

static int fail(const char *step) {
    std::printf("FAIL: %s\n", step);
    return 1;
}

static QByteArray fingerprint(const QByteArray &salt, const QByteArray &secret) {
    QCA::Hash sha256("sha256");
    sha256.update(QCA::SecureArray(salt));
    sha256.update(QCA::SecureArray(secret));
    return sha256.final().toByteArray();
}

int main() {
    QCA::Initializer init;

    // 1) 随机会话盐（16 字节）
    QCA::SecureArray salt = QCA::Random::randomArray(16);
    if (salt.size() != 16) return fail("random salt");
    std::printf("step1 random salt ok, len=%d\n", salt.size());

    // 2) 加盐 SHA-256 指纹
    const QByteArray secret = "psi-account@example.org:hunter2";
    QByteArray digest = fingerprint(salt.toByteArray(), secret);
    if (digest.size() != 32) return fail("sha256 digest size");
    std::printf("step2 salted sha256 ok, len=%d\n", digest.size());

    // 3) Base64 传输编码 → 解码回环比对
    QCA::Base64 encoder;
    QString wire = encoder.arrayToString(digest);
    if (wire.isEmpty()) return fail("base64 encode");
    QByteArray decoded = QByteArray::fromBase64(wire.toUtf8());
    if (decoded != digest) return fail("base64 roundtrip mismatch");
    std::printf("step3 base64 roundtrip ok, wire=%s\n", qPrintable(wire));

    // 4) 可重现性：同盐同口令二次计算一致；换盐必须不同
    if (fingerprint(salt.toByteArray(), secret) != digest) return fail("fingerprint not reproducible");
    if (fingerprint(QCA::Random::randomArray(16).toByteArray(), secret) == digest)
        return fail("different salt produced same fingerprint");
    std::printf("step4 reproducibility ok\n");

#ifdef __OHOS__
    // 鸿蒙特有断言：psi 在 OHOS 上所需的能力缺一不可。sha256/random/tls 全部
    // 由 qca-ossl 插件提供，故这同时是"插件在本平台正常加载"的运行时判据
    //（psi 多处 QCA::isSupported("tls") 门禁，缺失则 XMPP TLS 不可用）。
    const char *required[] = {"sha1", "sha256", "random", "tls"};
    for (const char *feature : required) {
        if (!QCA::isSupported(feature)) {
            std::printf("FAIL: OHOS capability missing: %s\n", feature);
            return 2;
        }
    }
    std::printf("step5 OHOS capability check ok (sha1/sha256/random/tls)\n");
#endif

    std::printf("consumer flow OK\n");
    return 0;
}
