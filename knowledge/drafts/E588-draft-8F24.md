# E588: libxml2 2.15.x 的 xmlGetLastError() 返回 const xmlError*，老代码用非 const xmlErrorPtr 接收报 discards qualifiers

## 错误特征
- 编译期：`assigning to 'xmlErrorPtr' (aka '_xmlError *') from 'const xmlError *' discards qualifiers` 或 `cannot initialize a variable of type 'xmlErrorPtr' with an rvalue of type 'const xmlError *'`
- 触发条件：C/C++ 项目在 libxml2 ≥2.15 上编译，代码直接用 `xmlErrorPtr`（非 const）接收 `xmlGetLastError()` 返回值。

## 触发条件
- `xmlGetLastError()` 在 libxml2 2.15 起返回 `const xmlError*`（错误对象只读）
- 老代码（如 scram 0.16.2 的 `src/xml.cc:31` 与 `src/xml.h:161`）声明/赋值给非 const `xmlErrorPtr`（typedef `_xmlError *`）

## 根因
libxml2 2.15 将 `xmlGetLastError()` 返回值 const 化，使错误对象不可被调用方修改。`xmlErrorPtr` 是非 const typedef，直接接收 `const xmlError*` 返回值触发 Clang 的 `discards qualifiers` 错误（严格模式）。

## 解决方案
把接收 `xmlGetLastError()` 返回值的变量/参数类型改为 `const xmlError*`：

```bash
sed -i 's/xmlErrorPtr xml_error = xmlGetLastError();/const xmlError *xml_error = xmlGetLastError();/' src/xml.cc
# 模板参数同理：T GetError(const xmlError *xml_error = nullptr)
```

错误对象仅需只读访问（message/file/line 字段），const 化不影响用法。

## 验证证据
- 命令：修改 `src/xml.cc` 与 `src/xml.h` 类型后重新编译
- 结果：scram 0.16.2 编译成功；上游测试 `scram_tests` 68/68 通过（525 assertions）；conan-verify G0-G4 + L2/L4/L5 全部 PASS
- 补丁：`archives/s/scram/0.16.2/patches/0004-src-xml.cc.patch` 与 `0005-src-xml.h.patch`

## 适用边界
- 所有直接使用 `xmlGetLastError()` 返回值的 C/C++ 项目，在 libxml2 ≥2.15 编译时适用
- 与 libxml2 2.14 及更早版本兼容（返回非 const 时 const 接收同样合法）

## 不适用边界
- 通过 `xmlErrorPtr` API 主动修改错误对象的代码（罕见）；此类需改用 libxml2 提供的可变接口
