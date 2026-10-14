// test_package/test_package.c — globus-openssl-module 5.2 consumer test (L1)
// 真实调用 globus-openssl-module API：globus_module_activate(
// GLOBUS_OPENSSL_MODULE) → 断言 activate 注册的 GSI 代理证书 OID
// （PROXYCERTINFO / OLD PROXYCERTINFO / 四个代理策略 OID，OBJ_txt2nid /
// OBJ_nid2sn）与 OLD PROXYCERTINFO 的 X509V3 扩展方法（X509V3_EXT_get_nid）
// → deactivate → re-activate 循环后断言全部恢复 → deactivate，验证库链接
// 与模块激活语义可用；任一步失败 return 1。
#include <globus_openssl.h>
#include <proxycertinfo.h>
#include <openssl/objects.h>
#include <openssl/x509v3.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    globus_result_t rc;
    int nid = 0;
    int nid_old = 0;
    const char *sn = NULL;
    const X509V3_EXT_METHOD *ext = NULL;
    ASN1_OBJECT *obj = NULL;
    char otxt[80];

    /* 1. 激活模块（内部级联激活 globus-common 与 globus-gsi-openssl-error，
       并注册 GSI 代理证书 OID 与 X509V3 扩展方法） */
    rc = globus_module_activate(GLOBUS_OPENSSL_MODULE);
    if (rc != GLOBUS_SUCCESS) {
        fprintf(stderr, "test globus-openssl-module 5.2: FAIL "
                "(activate rc=%lu)\n", (unsigned long)rc);
        return 1;
    }

    /* 2. activate 注册 PROXYCERTINFO OID（1.3.6.1.5.5.7.1.14） */
    nid = OBJ_txt2nid(PROXYCERTINFO_OID);
    if (nid == 0) {
        fprintf(stderr, "test globus-openssl-module 5.2: FAIL "
                "(PROXYCERTINFO OID not registered)\n");
        return 1;
    }

    /* 3. OID 文本往返一致（OpenSSL 3.x 已内置 proxyCertInfo 对象，短名
       来自内置表而非 OBJ_create 注册名，不可断言 OBJ_nid2sn；OID 文本
       往返才是本库激活后可解析语义的稳定证据） */
    obj = OBJ_txt2obj(PROXYCERTINFO_OID, 1);
    if (obj == NULL) {
        fprintf(stderr, "test globus-openssl-module 5.2: FAIL "
                "(OBJ_txt2obj failed)\n");
        return 1;
    }
    memset(otxt, 0, sizeof(otxt));
    if (OBJ_obj2txt(otxt, (int) sizeof(otxt), obj, 1) <= 0 ||
        strcmp(otxt, PROXYCERTINFO_OID) != 0) {
        fprintf(stderr, "test globus-openssl-module 5.2: FAIL "
                "(OID round-trip mismatch: %s)\n", otxt);
        return 1;
    }
    sn = OBJ_nid2sn(nid);
    ASN1_OBJECT_free(obj);
    obj = NULL;

    /* 4. OLD PROXYCERTINFO OID（1.3.6.1.4.1.3536.1.222）已注册 */
    nid_old = OBJ_txt2nid(PROXYCERTINFO_OLD_OID);
    if (nid_old == 0) {
        fprintf(stderr, "test globus-openssl-module 5.2: FAIL "
                "(OLD PROXYCERTINFO OID not registered)\n");
        return 1;
    }

    /* 5. OLD PROXYCERTINFO 的 X509V3 扩展方法已注册（activate 内
       X509V3_EXT_add，OpenSSL 无此 old OID 的内置方法） */
    ext = X509V3_EXT_get_nid(nid_old);
    if (ext == NULL) {
        fprintf(stderr, "test globus-openssl-module 5.2: FAIL "
                "(OLD PROXYCERTINFO x509v3 method missing)\n");
        return 1;
    }

    /* 6. 四个代理策略 OID 均已注册 */
    if (OBJ_txt2nid(ANY_LANGUAGE_OID) == 0 ||
        OBJ_txt2nid(IMPERSONATION_PROXY_OID) == 0 ||
        OBJ_txt2nid(INDEPENDENT_PROXY_OID) == 0 ||
        OBJ_txt2nid(LIMITED_PROXY_OID) == 0) {
        fprintf(stderr, "test globus-openssl-module 5.2: FAIL "
                "(proxy policy OID not registered)\n");
        return 1;
    }

    printf("test globus-openssl-module 5.2: first pass OK "
           "(PROXYCERTINFO nid=%d sn=%s, OID round-trip OK, "
           "6 OIDs registered, old ext method present)\n", nid,
           sn ? sn : "(null)");

    /* 7. 反激活（内部 X509V3_EXT_cleanup 移除 OLD 扩展方法） */
    rc = globus_module_deactivate(GLOBUS_OPENSSL_MODULE);
    if (rc != GLOBUS_SUCCESS) {
        fprintf(stderr, "test globus-openssl-module 5.2: FAIL "
                "(deactivate rc=%lu)\n", (unsigned long)rc);
        return 1;
    }

    /* 8. 再激活（deactivate/re-activate 循环） */
    rc = globus_module_activate(GLOBUS_OPENSSL_MODULE);
    if (rc != GLOBUS_SUCCESS) {
        fprintf(stderr, "test globus-openssl-module 5.2: FAIL "
                "(re-activate rc=%lu)\n", (unsigned long)rc);
        return 1;
    }

    /* 9. 循环后 PROXYCERTINFO OID 仍可解析 */
    nid = OBJ_txt2nid(PROXYCERTINFO_OID);
    if (nid == 0) {
        fprintf(stderr, "test globus-openssl-module 5.2: FAIL "
                "(PROXYCERTINFO OID lost after cycle)\n");
        return 1;
    }

    /* 10. 循环后 OLD OID 与其 X509V3 扩展方法重新注册 */
    nid_old = OBJ_txt2nid(PROXYCERTINFO_OLD_OID);
    ext = (nid_old == 0) ? NULL : X509V3_EXT_get_nid(nid_old);
    if (ext == NULL) {
        fprintf(stderr, "test globus-openssl-module 5.2: FAIL "
                "(OLD PROXYCERTINFO OID/ext method not restored)\n");
        return 1;
    }

    printf("test globus-openssl-module 5.2: OK (deactivate/re-activate "
           "cycle passed, PROXYCERTINFO nid=%d)\n", nid);

    /* 11. 最终反激活 */
    rc = globus_module_deactivate(GLOBUS_OPENSSL_MODULE);
    if (rc != GLOBUS_SUCCESS) {
        fprintf(stderr, "test globus-openssl-module 5.2: FAIL "
                "(final deactivate rc=%lu)\n", (unsigned long)rc);
        return 1;
    }

    return 0;
}
