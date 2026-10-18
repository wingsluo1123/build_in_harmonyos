# E999 draft — C++17 removed the `register` storage class specifier

> 草稿条目（draft: true），待主编审核后提升为正式 E 编号。
> 结构化数据：[E999-draft-cxx17-register-storage-class.kv](E999-draft-cxx17-register-storage-class.kv)
> 发现来源：plast 2.3.2（2017 年源码）在 OHOS `cppstd=17` profile 下的静态适配分析。

## 错误特征

```text
error: ISO C++17 does not allow 'register' storage class specifier [-Wregister]
```

GCC 侧对应：

```text
error: ISO C++17 does not allow 'register' storage class specifier
```

## 触发条件

三个条件同时成立时才会出现：

1. 目标 profile 使用 C++17（本仓库的 `ci/conan/profiles/ohos-aarch64` 固定
   `compiler.cppstd=17`，Conan 的 `CMakeToolchain` 会向所有 C++ 目标传递
   `-std=c++17`）；
2. 源码是 C++17 之前的遗留代码，仍把 `register` 当存储类说明符使用；
3. 该翻译单元**确实参与编译**（很多库的 `register` 出现在测试或不参与构建的子目录里，
   因此不会暴露）。

`register` 在 C++11 被弃用、C++14 仅作警告、**C++17 直接从语言中移除**。
它本身只是“建议放入寄存器”的无效提示，编译器早已忽略，因此删除它没有任何语义影响。

注意：C 语言不受影响（C17 仍允许 `register`，C23 才弃用），所以
`foo.h` 里的 `register int len;` 只要只被 `.c` 文件包含就不会报错。

## 影响范围

- 任意在 OHOS 上以 `cppstd=17`（profile 默认）编译的、源码年代早于 C++11 的 C++ 项目；
- 典型表现为“大工程编译到很后面才突然失败”，容易误判为平台专有问题；
- 同一个源码在 `-std=c++14` 下只会得到 `-Wregister` 警告，因此本机若用旧标准试编
  无法复现，跨环境排查时容易走偏。

## 定位命令

```bash
# 1) 先扫一遍源码，编译前就能发现
grep -rn --include=*.cpp --include=*.hpp -E '^[[:space:]]*register[[:space:]]+' src/

# 2) 用一个最小样例确认当前工具链行为
echo 'int main(){register int i=0;return i;}' | clang++ -x c++ -std=c++17 - -o /dev/null
```

## 推荐方案（priority 1）

删除该 `register` 关键字，保持项目继续用 C++17：

```bash
sed -i -E 's/^([[:space:]]*)register[[:space:]]+/\1/' src/algo/stats/impl/StatisticsPlastn.cpp
```

实测案例（plast 2.3.2）：

```diff
--- a/src/algo/stats/impl/StatisticsPlastn.cpp
+++ b/src/algo/stats/impl/StatisticsPlastn.cpp
@@ -412,7 +412,8 @@ double GlobalParametersPlastn::karlinLHtoK(Blast_ScoreFreq* sfp, double lambda,
 	/*highest and lowest possible alignment scores for current length*/
 	int32_t            lowAlignmentScore, highAlignmentScore;
 	int32_t            first, last; /*loop indices for dynamic program*/
-	register double innerSum;
+	/* 'register' is not a storage class specifier any more in C++17 */
+	double innerSum;
```

补丁可向上游提交（P005）：上游在任何标准下都不需要这个关键字。

## 回退方案（priority 2）

当该源码改动无法随配方携带时，可在配方的 `generate()` 中把该工程钉到 C++14：

```python
def generate(self):
    tc = CMakeToolchain(self)
    tc.cache_variables["CMAKE_CXX_STANDARD"] = "14"
    tc.generate()
```

代价：与 `settings.compiler.cppstd=17` 声明的包 ID 不一致，且会掩盖后续其它
C++17 移除项，只应作为临时手段。

## ⛔ 禁止

```c
#define register            /* 禁止：用宏抹掉关键字 */
```

```text
-Wno-register / -Wno-error=register   # 禁止：只压诊断不修代码
```

理由：`register` 是**语言层面被移除**的语法，而不是某个平台的诊断差异；
压掉诊断不会让代码合法，只会把同一类问题（`std::auto_ptr`、
`std::unary_function`/`binary_function`、动态异常规格 `throw(T)`、
`std::random_shuffle`）推迟到更晚才爆炸。

## 关联

- **E293** — *2003 年代旧 C++ 代码在 C++17 标准下动态异常规范 `throw(...)` 与
  `register` 关键字编译失败*：**E293 已覆盖本模式**（其 error signature 就含
  `ISO C++17 does not allow 'register' storage class specifier`）。本条目是该模式在
  plast 2.3.2 上的一个**实例与补充证据**，新增内容是：`grep` 式预扫描命令、
  「`register` 被删后语义不变」的依据、以及禁止用 `#define register` / `-Wno-register`
  掩盖的边界说明，不主张新模式。
- **E130** — OHOS SDK libc++ 头文件要求最低 C++17：与本条目方向相反、互为补充
  （E130 处理“本该用 C++17 却用了 C++11”，本条目处理“被迫用 C++17 后遗留源码里的
  C++17 移除项”）。
- **P005** — 补丁必须可向上游提交
- **P007** — `-Werror` 禁用应精准到具体 warning 类别（本条目禁止用禁用诊断代替修代码）
- **P013** — 平台限制必须降级而非绕过

---
*2026-10-15 · 来源：plast 2.3.2 适配（archives/p/plast/2.3.2/patches/0006-cxx17-drop-register.patch）*
