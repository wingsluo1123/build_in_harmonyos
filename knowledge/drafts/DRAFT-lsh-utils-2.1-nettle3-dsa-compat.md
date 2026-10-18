# DRAFT-lsh-utils-2.1-nettle3-dsa-compat：nettle 2.x 消费者代码在 nettle 3.x 上的 DSA 接口搬家

> Contributor: wanderlust_0823 | Status: Draft | Updated: 2026-10-18
> Source: lsh-utils 2.1（GNU lsh）HarmonyOS PC 适配
> 对应：`knowledge/drafts/DRAFT-lsh-utils-2.1-nettle3-dsa-compat.kv`
> 相关：E1656（gmp/6.3.0.1 未导出 include，另一件事）、E007/E011（同一适配里的 autotools 侧问题）

## 现象（逐条给原文）

在一个 2013 年、针对 **nettle 2.x** 写的 C 工程上编译，先后出现三类错误：

```text
# 1) 编译期：结构体在公开头里已不存在
src/spki/verify.c:70:25: error: variable has incomplete type 'struct dsa_public_key'
  struct dsa_public_key dsa;
                        ^
src/spki/verify.c:70:10: note: forward declaration of 'struct dsa_public_key'

# 1b) 同一处的连带症状（隐式声明）
src/spki/verify.c:74:3: warning: call to undeclared function 'dsa_public_key_init'
src/spki/verify.c:82:6: warning: call to undeclared function 'dsa_sha1_verify_digest'
src/spki/verify.c:85:3: warning: call to undeclared function 'dsa_public_key_clear'

# 2) 补上 compat 头之后：调用点形参数量对不上
src/spki/verify.c:79:56: error: too few arguments to function call, expected 6, have 5
                                     RSA_KEYSIZE_LIMIT, DSA_SHA1_Q_BITS, &key->sexp)
                                                                                   ^
.../nettle/dsa.h:153:1: note: 'nettle_dsa_keypair_from_sexp_alist' declared here
```

三处症状是同一根因的不同阶段：**类型没了 → 函数没了 → 函数签名变了**。
只补 include 会停在 2)，只改签名会停在 1)。

## 根因

nettle 3.0 把 DSA 的"整键"接口整体移出了公开头。以 `nettle/3.10.2.1` 为例：

| 旧接口（nettle 2.x，工程里在用） | nettle 3.10.2.1 的 `<nettle/dsa.h>` | 现在在哪 |
|---|---|---|
| `struct dsa_public_key`（p,q,g,y） | **不存在**（`grep 'struct dsa_public_key' dsa.h` 0 命中） | `<nettle/dsa-compat.h>` |
| `struct dsa_private_key`（x） | **不存在** | `<nettle/dsa-compat.h>` |
| `dsa_public_key_init/_clear`、`dsa_private_key_init/_clear` | 不存在 | `<nettle/dsa-compat.h>`（`#define` 到 `nettle_*`） |
| `dsa_sha1_sign_digest` / `dsa_sha1_verify_digest`（及 sha256 版） | 不存在 | `<nettle/dsa-compat.h>` |
| `dsa_generate_keypair(pub, priv, ...)` | 被换成 `dsa_generate_keypair(params, mpz_t pub, mpz_t key, ...)` | compat 头用 `#define dsa_generate_keypair nettle_dsa_compat_generate_keypair` **换回旧语义** |

nettle 3 的公开 DSA API 变成了 `struct dsa_params{p,q,g}` + 裸 `mpz_t pub` / `mpz_t priv`：

```c
/* nettle 3.10.2.1 include/nettle/dsa.h */
struct dsa_params { mpz_t p; mpz_t q; mpz_t g; };
struct dsa_signature { mpz_t r; mpz_t s; };

int dsa_sign(const struct dsa_params *params, const mpz_t x, ...);
int dsa_verify(const struct dsa_params *params, const mpz_t y, ...);
int dsa_keypair_from_sexp_alist(struct dsa_params *params, mpz_t pub, mpz_t priv,
                                unsigned p_max_bits, unsigned q_bits,
                                struct sexp_iterator *i);
```

## 关键判断：compat 头有真实现，不是空壳（先探针再动手）

踩这条最容易走错的路是"以为 compat 头只是声明、于是自己重写 DSA 层"。先做探针：

```sh
$ nm -g <nettle-pkg>/lib/libhogweed.a | grep -E 'T (_?nettle_)?(dsa_public_key_init|dsa_compat_generate_keypair|dsa_sha1_verify_digest)$'
0000000000000000 T nettle_dsa_public_key_init
0000000000000000 T nettle_dsa_compat_generate_keypair
0000000000000000 T nettle_dsa_sha1_verify_digest
```

三个都是 **T（已定义）**，且 `ar` 列表里能看到 `dsa-compat.o` / `dsa-compat-keygen.o`。
注意 DSA/RSA 这些公钥函数在 **libhogweed.a** 而不在 libnettle.a——只在 libnettle 里 grep 会误判"没有"。

## 处置（两处改动，零重写）

1. **补 include**：在用到旧 DSA 接口的翻译单元里，紧跟 `<nettle/dsa.h>` 之后加
   `#include <nettle/dsa-compat.h>`（该头自身会再 include dsa.h，顺序无所谓，但跟着写最直观）。
2. **对齐新增的 `params` 形参**：`dsa_keypair_from_sexp_alist` 从
   `(pub, [priv,] p_max_bits, q_bits, i)` 变成 `(params, pub, priv, p_max_bits, q_bits, i)`。
   兼容头的自述给了官方桥接方式：

   > Layout must be identical, since this is cast to a struct dsa_param pointer
   > for calling _dsa_sign and _dsa_verify

   即 `struct dsa_public_key{p,q,g,y}` 的前三个成员就是 `struct dsa_params`，于是：

   ```c
   struct dsa_public_key dsa;            /* compat 头提供的布局 */
   dsa_public_key_init(&dsa);            /* 仍是 mpz_init 四个成员 */

   /* 只解析公钥：priv 传 NULL */
   dsa_keypair_from_sexp_alist((struct dsa_params *) &dsa, dsa.y, NULL,
                               p_max_bits, q_bits, i)

   /* 同时解析私钥：priv 传对应 dsa_private_key 的 x */
   dsa_keypair_from_sexp_alist((struct dsa_params *) &verifier->key,
                               verifier->key.y, signer->key.x,
                               p_max_bits, q_bits, i)
   ```

   本案例共 3 处调用点（`src/spki/verify.c` 1 处、`src/dsa.c` 2 处），都是这一个模式。

## 适用边界与反例

- **不适用**：nettle 4.x（已删除 `dsa-compat.h`）。目标版本要先用 `test -f include/nettle/dsa-compat.h` 确认。
- **不需要动**：RSA 侧。nettle 3 的 `<nettle/rsa.h>` 仍然公开 `struct rsa_public_key` /
  `struct rsa_private_key`，`rsa_keypair_from_sexp_alist(pub, priv, limit, i)` 也仍是 4 参——
  本案例把 DSA 改完之后 RSA 路径**零改动**通过；看到"nettle 3 不兼容"就整体重写会把工作量放大一个量级。
- **别做的事**：自造 `struct dsa_public_key` 定义（与头里的声明冲突、且与 compat 实现的对象布局对不上）；
  用 `-Ddsa_public_key=...` 之类宏改名绕过（只骗过编译器，链接期照样炸）；把 nettle 降到 2.x
  （仓内往往只有 3.x，且降版会让其它依赖回退）。
- 另一个容易混进来的方向：`-fgnu89-inline` / `-fcommon` 是**同时**出现的另一类问题
  （GNU89 inline 语义、tentative definition），与本条无关，别混在一个根因里。

## 查重与新增价值

- `grep -rl 'dsa-compat' knowledge/` → **0 命中**；nettle 相关只有 E1656（讲 gmp/6.3.0.1 的
  includedirs 为空导致 `<gmp.h>` 找不到）与 E299/E747（取源），**完全不覆盖本机制**。
- 复用面：凡"针对 nettle 2.x 写的消费者 + 仓内只有 nettle 3.x"的组合都会先后撞上这三类症状；
  这条给出"先探针 libhogweed 的 T 符号 → 再 include compat + 对齐形参"的两步法，
  避免直接跳进"重写 DSA 层"的高成本分支。

## 实证出处

- 包：`archives/l/lsh-utils/2.1`（GNU lsh 2.1，平台任务 8572 适配）
- 改动：`patches/0002-nettle3-dsa-compat.patch`（3 文件，66 行）
- 依赖：`nettle/3.10.2.1`（rev `dd70eb7fecab6fa13ab06d1f9cf13412`）+ `gmp/6.3.0`
- 验证：补丁后该包全量编译通过，`lsh-keygen --version` → `lsh-keygen-2.1`；
  上游 `make check` 里所有依赖 DSA/公钥的编译型用例（rsa、dsa、spki-tag、cdsa-reduce、
  check-signature、delegate、reduce 等）全部 PASS；`lsh-decrypt-key` 往返用例亦 PASS。
