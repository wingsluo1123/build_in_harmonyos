# OpenSSL 3.x 栈上 EVP_MD_CTX 悬垂导致 X509_REQ_free bad-free

## 场景

libest 1.0.0（Cisco EST 库，2014 年代码）适配 HarmonyOS PC（aarch64，clang 15，
链接 ohpcd 制品仓 openssl/3.5.6.1）。上游单测 US898/US899 在修复 OpenSSL 3.x
私有 API 迁移后，运行时以 ASan 复现崩溃：

```
==ERROR: AddressSanitizer: attempting free on address which was not malloc()-ed: 0x007a62413458
  #5 ASN1_item_free (libcrypto.so.3)
  #6 us899_test2 us899.c:445:5   <- X509_REQ_free(csr)
Address 0x007a62413458 is located in stack of thread T0 at offset 24 in frame
  #0 est_client_X509_REQ_sign est_client.c:77
```

## 症状

- 测试进程退出码 134/139（Signal 6 / SIGSEGV），US898/US899 无 Run Summary
- ASan 明确给出：被 free 地址位于 `est_client_X509_REQ_sign` 栈帧（函数早已返回）→ 悬垂指针
- 该函数内是 `EVP_MD_CTX mctx` 栈上局部变量（1.x 写法 `EVP_MD_CTX_init(&mctx)`）

## 根因

OpenSSL 3.x 中 `EVP_MD_CTX` 是不透明结构（内部含指针/编码缓存），尺寸远超 1.x 时期。
栈上分配 + `EVP_MD_CTX_init` + 把 `&mctx` 交给 `X509_REQ_sign_ctx` 后，签名/ASN.1 编码
路径会把 mctx 内部地址写入 X509_REQ 关联结构；函数返回后栈帧失效，最终
`X509_REQ_free(csr)` 对栈地址执行 `free` → bad-free。

1.x 的 `EVP_MD_CTX_init/cleanup` 栈分配模式在 OpenSSL 3.x 属未定义行为，本平台必现。

## 修复

栈分配 → 堆分配（补丁 `0010-src-est-est_client.c.patch`）：

```c
/* 旧 */
EVP_MD_CTX mctx;
EVP_MD_CTX_init(&mctx);
if (!EVP_DigestSignInit(&mctx, &pkctx, md, NULL, pkey)) return 0;
rv = X509_REQ_sign_ctx(x, &mctx);
EVP_MD_CTX_cleanup(&mctx);

/* 新 */
EVP_MD_CTX *mctx = EVP_MD_CTX_new();
if (mctx == NULL) return 0;
if (!EVP_DigestSignInit(mctx, &pkctx, md, NULL, pkey)) { EVP_MD_CTX_free(mctx); return 0; }
rv = X509_REQ_sign_ctx(x, mctx);
EVP_MD_CTX_free(mctx);
```

断言与测试语义不变（未放宽任何 rv 断言）。修复后 US898 11/11、US899 18/18
各连续两次完整跑完（exit 0，无 ASan 报告）。

## 验证

```bash
# 修复前（ASan）
clang -fsanitize=address -g -O0 -o rn-US899-fullasan <objs> && ./rn-US899-fullasan
#   -> Signal 6 (core dumped)，bad-free 栈帧指向 est_client_X509_REQ_sign

# 修复后（ASan，连续两次）
./rn-US899-fullasan  # exit 0, tests 18/18, asserts 124/124, ASan 报告 0
```

## 适用边界 / 反例 / 限制

- 适用：所有用栈分配 `EVP_MD_CTX` + `EVP_MD_CTX_init` 再交给 `X509_REQ_sign_ctx` /
  `X509_sign_ctx` 的 C/C++ 老库
- 反例：仅修正 `clear_csr_pop` 的 `X509_ATTRIBUTE_free` 所有权而不触及栈分配无效
  （libest r10 两次尝试实测仍崩溃）；禁止无新证据重复同一失败修复
- 限制：悬垂对象不一定是 EVP_MD_CTX——按 ASan 栈帧逐点排查（编码缓存 enc、
  `ASN1_STRING_set` 栈缓冲、`X509_ATTRIBUTE` 值）；与 E249（shared/owned 标志）
  错误签名相似但机制不同

## 关联

- 相似：E249
- 引用补丁：`patches/0010-src-est-est_client.c.patch`
