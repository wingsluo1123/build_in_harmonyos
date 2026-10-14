# 两个 mangled 名完全相同的类型被判为"不同类型"：libc++ 的 `typeid` hash 在跨 DSO 的 RTTI 副本之间不可靠

> Draft: DRAFT-PYTORCH-21301-TYPEID-HASH-DIFFERS-ACROSS-DSO-RTTI-COPIES
> Stem: `pytorch-2.13.0.1-typeid-hash-differs-across-dso-rtti-copies` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-PYTORCH-21301-TYPEID-HASH-DIFFERS-ACROSS-DSO-RTTI-COPIES
- **严重度**: 2
- **类别**: abi|rtti|shared-library|upstream-defect
- **触发工具**: conan|clang|c++
- **阶段**: runtime

## 症状

类型擦除容器在**跨模块**取回一个值时报类型不匹配，而**报错文本里两侧打印的类型名一字不差**：

```
C++ exception with description "Expected argument #1 to be of type
std::__n1::optional<c10::ArrayRef<long>>, but received value of type
std::__n1::optional<c10::ArrayRef<long>>"
```

即：容器里**确实**存着这个类型、写法也没错，但 `typeid(T).hash_code() == stored.hash_code()` 判定不成立。

本项目中的实例是 pytorch 的 `torch::nn::AnyValue::try_get()`（`any_value.h`）：上游测试
`SequentialTest.ModuleForwardMethodOptionalArg` 因此失败，而同一个二进制在另一份构建产物上通过。

## 根因分析

libc++ 的 `type_info` 有**三种比较实现**（见 `<c++/v1/typeinfo>` 的
`_LIBCPP_TYPEINFO_COMPARISON_IMPLEMENTATION`）：

| 值 | 名称 | 语义 |
|---|---|---|
| 1 | `Unique` | **默认**（非 COFF、非 Apple）。假设全程序只有一份 RTTI：`hash_code()` 直接由**类型名指针**导出，比较也走指针 |
| 2 | `NonUnique` | 不假设唯一：`hash_code()` 对类型名**字符串**算 hash，比较做深比较（libc++ 认为"链接器可能没合并 RTTI"时用这套语义） |
| 3 | `NonUniqueARMRTTIBit` | Apple arm64 专用的高位标记法 |

实测本机 SDK 的 libc++ 取的是 **1（Unique）**：对任意 ATen TU 预处理后可见
`#define _LIBCPP_TYPEINFO_COMPARISON_IMPLEMENTATION 1`。

于是在**两份 RTTI 副本未被动态链接器合并**时，`hash_code()` 变成"两个不同指针各自的 hash"，直接比较必然不等。副本从哪来：

- 打包的库（本例 `libtorch_cpu.so`）编译时带 `-fvisibility=hidden`，对某个头文件实例化类型只发出 **local** 的 RTTI 符号——静态符号表里是 `d`，而 `.dynsym` 中**根本不存在**；
- 消费者（可执行文件/另一个 .so）也实例化了同一类型，发出默认可见性的**弱**副本；
- 动态链接器**不能**用 local 符号做跨模块合并 → 运行时存在两份 RTTI。

判定线索就在报错文本：**"期望类型"与"实际类型"打印得一模一样**时，不要去怀疑类型拼写或模板参数，直接怀疑 RTTI 副本没合并。

## 判定方法

1. 看异常文本：两侧类型名逐字符相同 → 指向 RTTI 副本问题，而非类型写错。
2. 查该类型的 typeinfo 在库里的绑定：

```sh
nm -D <lib.so> | grep '_ZTI.*<mangled-type>'   # 动态符号表：本例无输出 = 未导出
nm    <lib.so> | grep '_ZTI.*<mangled-type>'   # 静态符号表：本例为 "d" = local
```

3. **脱离 pytorch 的最小复现**（两个 DSO，一个 `-fvisibility=hidden`、一个默认）：

```sh
d=$(mktemp -d)
cat > $d/a.cpp <<'EOF'
#include <optional>
#include <typeinfo>
extern "C" __attribute__((visibility("default"))) unsigned long f() {
    return typeid(std::optional<long>).hash_code();
}
EOF
cat > $d/m.cpp <<'EOF'
#include <cstdio>
#include <optional>
#include <typeinfo>
extern "C" unsigned long f();
int main() {
    std::printf("exe=%lu dso=%lu\n",
        typeid(std::optional<long>).hash_code(), f());
}
EOF
clang++ -std=c++17 -fPIC -shared -fvisibility=hidden -o $d/liba.so $d/a.cpp
clang++ -std=c++17 -o $d/m $d/m.cpp -L$d -la -Wl,-rpath,$d
$d/m
```

实测结果：

| DSO 编译方式 | `name()` | `hash_code()` | `strcmp(name)` |
|---|---|---|---|
| `-fvisibility=hidden` | 两侧同为 `NSt4__n18optionalIlEE` | **不同**（exe=373858220048 / dso=390721439352） | 相等 |
| 默认可见性 | 两侧同 | 相同（均 370141349968） | 相等 |

> 注意：hidden 变体里被外部调用的入口函数必须显式标
> `__attribute__((visibility("default")))`，否则连链接都过不去——这本身就是 "hidden 会传染" 的旁证。

## 处置

**保留 hash 快路径，hash 不等时回退比较 mangled 名**（即 libc++ `NonUnique` 的语义）：

```cpp
if (typeid(T).hash_code() == type_info().hash_code()) {
    return &static_cast<Holder<T>&>(*content_).value;
}
// hash 不等：可能是两份 RTTI 副本未被合并（libc++ "Unique" 实现下 hash 由类型名指针导出）。
// 退化为名字比较，类型判定不放松：不同类型的 mangled 名必不同。
if (std::strcmp(typeid(T).name(), type_info().name()) == 0) {
    return &static_cast<Holder<T>&>(*content_).value;
}
return nullptr;
```

取舍与替代方案：

- **不要**改成"只用名字比较"——白白牺牲快路径；
- **不要**靠 `-fvisibility=default` 重编整个库来绕——会暴露全部内部符号，且有 ODR 风险；
- 可选：编译期把 `_LIBCPP_TYPEINFO_COMPARISON_IMPLEMENTATION` 设为 2。但那要求**库与所有消费者同时对 libc++ 生效**，包管理器难以保证，故优先在选择调用点修。

## 适用范围

所有把"类型擦除 + `typeid` 比较"用于**跨模块边界**的库：`std::any` 式容器、插件/扩展系统、序列化注册表、
C++ 前端模块容器（如 `torch::nn::AnyModule`）。该现象**与平台无关**（任何 ELF 上都可能出现），
只在"库以 hidden visibility 编译、消费者另有默认可见性副本"的打包方式下最容易发生——
用 `-fvisibility=hidden` 打包公共库时尤其要留意这一点。
