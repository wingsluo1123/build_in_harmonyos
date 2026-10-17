# OpenSSL 3.x 私有 API/结构迁移

## 场景

libest 1.0.0（Cisco EST 库，2014 年代码，autotools + OpenSSL 1.x 私有 API）适配到
HarmonyOS PC（aarch64，clang 15），链接 ohpcd 制品仓 openssl/3.5.6.1。首次编译
`make` 在 src/est 和 example/ 出现三类结构性错误：

## 症状

```
src/est/est.c:1012: error: call to undeclared function 'c2i_ASN1_OBJECT'
src/est/est_client.c:80: error: variable has incomplete type 'EVP_MD_CTX'
src/est/est_client.c:559: error: incomplete definition of type 'struct x509_st'
example/client/estclient.c:170: error: incomplete definition of type 'struct x509_st'
example/server/estserver.c:116: error: incomplete definition of type 'struct dh_st'
ld.lld: error: duplicate symbol: e_ctx_ssl_exdata_index
```

- 编译期：`call to undeclared function`（内部函数被移除）与
  `incomplete definition of type`（结构体不透明化）两类并存，改完一类还会继续暴露下一类
- 链接期：头文件里非 extern 的全局变量定义在多个翻译单元包含后产生 duplicate symbol
- 错误与**具体符号**强相关，逐个符号迁移即可闭环，不存在"全局开关"

## 根因

OpenSSL 3.x（3.5.6）把 1.x 时代的内部函数与私有结构体移出公开头文件或整体删除：

| 1.x 写法 | 3.x 现状 | 迁移目标 |
|---|---|---|
| `c2i_ASN1_OBJECT(NULL, &p, len)` | 内部函数移除 | 回卷到 tag 后 `d2i_ASN1_OBJECT` |
| 栈 `EVP_MD_CTX mctx` + `EVP_MD_CTX_init/cleanup` | 不透明结构 | `EVP_MD_CTX_new/free` 指针 |
| `cert->sig_alg/->signature/->name` | 结构体不透明 | `X509_get0_signature` / `X509_NAME_oneline(X509_get_subject_name())` |
| `csr->signature`、`req->req_info->pubkey` | 不透明 | `X509_REQ_get0_signature` / `X509_REQ_get_pubkey` |
| `attr->single/->value.set` | 不透明 | `X509_ATTRIBUTE_count` + `X509_ATTRIBUTE_get0_type` |
| `cert->cert_info->extensions` | 不透明 | `X509_get_ext_count` + `X509_get_ext` 组装栈 |
| `dh->p/->g/->length` | 不透明 | `BN_bin2bn` + `DH_set0_pqg` + `DH_set_length` |
| `FIPS_mode()` / `FIPS_mode_set(1)` | 移除 | `EVP_default_properties_is_fips_enabled(NULL)` / `EVP_default_properties_enable_fips(NULL, 1)` |
| `BIO_s_file_internal()` | 移除 | `BIO_s_file()` |
| 头文件 `int e_ctx_ssl_exdata_index;` | -fno-common 下 dup symbol | 头文件改 `extern`，定义留在单一 .c |

## 方案

逐符号机械迁移（完整清单见 .kv rec_command 与 patches/0008-0012）。关键点：

1. **c2i_ASN1_OBJECT → d2i_ASN1_OBJECT 必须用 tlv_start 回卷**：调用点先在
   `ASN1_get_object(&string,&len,&tag,&xclass,out_len)` **之前**记录
   `const unsigned char *tlv_start = string;`，随后 `obj_p = tlv_start`，
   `d2i_ASN1_OBJECT(NULL, &obj_p, (long)((string - tlv_start) + len))`，
   解析后 `string = obj_p` 保持循环游标正确。
   **关键（r14 实证）**：`ASN1_get_object()` 成功时返回 **0x00**（既非头长也非
   总长），所以 j=0 时 `obj_p = string - (j - len)` 变成 `string + len`，指针越过
   内容跳到垃圾位置，且 d2i 以 maxlen=0 调用**必然失败**；`string - j` 传 j
   同样错误（j=0 不回退且长度 0）。est_get_attributes_helper 第二处曾用
   `string-(j-len)` 恒失败，已改为 tlv_start 模式并补充真实验证用例
   （DER OID challengePassword 识别成功 rv=0 nid=54）。
2. **EVP_MD_CTX 栈→堆**：`EVP_MD_CTX *mctx = EVP_MD_CTX_new()`，所有调用传指针，
   两个错误分支都要 `EVP_MD_CTX_free`，避免泄漏。
3. **X509 名字打印**：`current_cert->name` 无公开字段，改用
   `X509_NAME_oneline(X509_get_subject_name(cert), buf, sizeof buf)`。
4. **X509 扩展复制**：`cert->cert_info->extensions` 不透明，用
   `X509_get_ext_count` + `X509_get_ext` 逐条 push 进新建栈，
   传给 `X509_REQ_add_extensions` 后 `sk_X509_EXTENSION_pop_free`。
5. **DH 参数**：`dh->p/->g/->length` 无公开字段，用
   `BN_bin2bn` 生成 BIGNUM → `DH_set0_pqg(dh, p, NULL, g)`（转移所有权）→ `DH_set_length`。
6. **FIPS**：`FIPS_mode()` → `EVP_default_properties_is_fips_enabled(NULL)`；
   `FIPS_mode_set(1)` → `EVP_default_properties_enable_fips(NULL, 1)`（返回值语义一致：1=成功）。
7. **dup symbol**：est_locl.h 的 `int e_ctx_ssl_exdata_index;`（tentative definition）
   改 `extern int ...;`，真实定义保留在 est_client.c。

## 验证

- `make -j1` 直至全绿，`grep -cE 'error:'` = 0、`grep -c 'duplicate symbol'` = 0
- 全源码清点残留：`grep -rEn 'c2i_ASN1_OBJECT|FIPS_mode|FIPS_mode_set|BIO_s_file_internal|->sig_alg|->cert_info|->req_info|->signature' src/ example/` 归零
- `conan create` 干净构建（补丁全量重放）+ test_package 链接运行：
  `est_get_version / est_get_api_level / est_init_logger` 三项断言通过
- conan-verify G1-G4 + L2/L4/L5 全绿，W3 本地 CI（build_and_test.sh）L0 pass

## 适用边界

- 适用：C/C++ 老库直访 OpenSSL 1.x 内部函数/私有字段，迁移到 OpenSSL 3.x 的机械替换
- 不适用：仅单个宏改名（见 E162）；运行时符号解析（见 E509）；
  编译配置探测 OpenSSL 缺失（见 E412/E384）
- 反例：不得以"过门禁"为由把 FIPS 检查删成空壳（R8）；不得用 --build/--host 绕过
  configure（native 编译禁例 E007/E072）；grep 关键字归零才算迁移完成

## 限制

- 不同库残留符号清单不同，替换入口以本机 openssl 3.5.6 公开头文件为准
- dup-symbol 仅在使用 -fno-common 语义的链接器下必然复现；extern 化在任何情况下都是正确写法
- 本条目由 libest 1.0.0 单一实证沉淀，跨库复用前建议先跑 verification_cmd 清点
