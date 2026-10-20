# taopm 1.0：C++98 `ostringstream(char *, openmode)` 在 C++11 之后变成堆越界读

> 草稿（DRAFT）— 来自 taopm 1.0（`TaoPitch::createName()`），用 AddressSanitizer 在主机侧复现，
> 并在 OHOS 真机 `conan create` 中验证修复。
> 与 `.kv` 同 stem 配对：`knowledge/DRAFT-taopm-1.0-cxx98-ostringstream-buffer-ctor.kv`

## 问题

taopm 的 `TaoPitch` 用固定缓冲区拼音名（1999 年风格）：

```cpp
name=new char[12];
//ostrstream nameStream(name, 12);
std::ostringstream nameStream(name, std::ostringstream::out);
switch(wholesemi) { case 0: nameStream << "C"; break; ... }
nameStream << octave;
if (fractsemi>0) nameStream << "+" << fractsemi << "/100";
nameStream << std::ends;
```

这段代码在 C++17 下**编译零报错**，但仅构造一个
`TaoString s(TaoPitch(220.0f, TaoPitch::frq), 10.0f);` 就会崩：

```text
==25508==ERROR: AddressSanitizer: heap-buffer-overflow on address 0x...
READ of size 13 at 0x... thread T0
    #0 __asan_wrap_strlen
    #1 std::_Narrow_char_traits<char,int>::length
    #2 std::basic_string<...>::{ctor}
    #3 TaoPitch::createName() libtao/TaoPitch.cc:262
    #4 TaoPitch::TaoPitch(float) libtao/TaoPitch.cc:172
0x... is located 0 bytes to the right of 12-byte region
allocated by thread T0 here:
    #1 TaoPitch::createName() libtao/TaoPitch.cc:259
```

## 根因

- C++98 有 `basic_ostringstream(char *buf, openmode)`：流写进调用者给的定长缓冲区，
  `<< std::ends` 补 '\0'。这是当年"零分配拼串"的标准写法。
- C++11 删除了该重载。同一个调用改为匹配
  `explicit basic_ostringstream(const basic_string&, openmode)`：
  `char*` → `std::string`（对**未初始化**的 12 字节做 `strlen`）→ 堆越界读。
- 而且流此后的输出全写进自己的内部缓冲，`name` 里仍是垃圾数据；后续
  `asName()`/`strlen(name)`/`delete [] name` 还会第二次踩到。
- 上游之所以 20 年没炸：`Tao::main()` 在合成结束时 `exit(0)`，
  全局对象的析构与后续字符串使用都被跳过。**这是"编译通过 ≠ 适配完成"的典型样例。**

同一文件里还有两个传统内存缺陷（一并修掉）：

```cpp
this->name=new char[nameLength];      // 应为 nameLength+1，strcpy 会写越界
strcpy(this->name, pitchName);
```

```cpp
TaoPitch::TaoPitch() {}               // name 未初始化
TaoPitch::~TaoPitch() { delete [] name; }  // 析构未初始化指针
```

## 修复

```cpp
std::ostringstream nameStream(std::ostringstream::out);
...
const std::string result=nameStream.str();
delete [] name;
name=new char[result.size()+1];
strcpy(name, result.c_str());
```

- `new char[nameLength+1]`；`operator=` 加 `if (this==&p) return *this; delete [] name;`；
- 默认构造函数把 `name` 与三个 version 字段清零；
- 两个 float 构造函数在调用 `createName()` 前 `name=NULL`（`createName` 会先 delete）。

## 验证

- 主机 MSVC C++17 + `/fsanitize=address`：修复前复现上���堆越界，修复后同一路径无报告，
  `test_tao_api` 11/11 通过；
- OHOS 真机：`conan create` + `test_package` 全绿（r7/r8，`exit-code.txt = 0`）。

## 迁移检查清单（给同类老库）

1. `grep -rn "ostringstream\s*(\s*[A-Za-z_]"`、`grep -rn ostrstream`、`grep -rn "std::ends"`；
2. 把"写外部缓冲"的用法改为 `std::string` + 拷贝；
3. 顺手核对 `new char[strlen(x)]` + `strcpy` 的 off-by-one；
4. 用 ASAN 跑一次真实 API 路径（不是只编译）。
