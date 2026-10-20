# taopm 1.0：单位宏污染标准库头（include 顺序 / 标识符重名）

> 草稿（DRAFT）— 来自 taopm 1.0 的 `include/taodefs.h` 与 taoparse 生成模板。
> 与 `.kv` 同 stem 配对：`knowledge/DRAFT-taopm-1.0-unit-macros-vs-stl-headers.kv`

## 问题

`taodefs.h` 是 tao 脚本语法的"糖"层，定义了一批裸单词宏：

```c
#define Hz
#define secs
#define min      *60.0
#define msecs    /1000.0
#define samples  /44100.0
#define Param    float
#define If(CONDITION) if(CONDITION)
...
```

于是在 C++17 下，**只要库头先于标准库头被 include**，就会出现语法错误：

```text
C:\...\include\vector(1877): error C2059: 语法错误:“<tag>::*”
```

原因是 MSVC `<vector>::max_size()` 内是 `return (_STD min)(...)`，`min` 被展开成
`*60.0` → `(_STD *60.0)(...)`。libc++ 的 `<string>`/`<algorithm>` 等也有未加
`std::` 的 `min`。

taoparse 生成程序的模板原本正好是"库头在前、STL 在后"：

```cpp
#include "taodefs.h"
#include <cmath>
#include <iostream>
```

所以**每一个**由 `taoparse` 生成、或用户手写的 tao 程序都踩到这个坑。

另一条同源问题：`#define samples /44100.0` 会把标识符 `samples` 改写成 `/44100.0`，
所以测试程序里写 `std::vector<float> samples;` 直接变成
`std::vector<float> /44100.0;`。自测代码把字段改名为 `frames` 即可，
但这类"宏名即单位"的库必须在使用说明里写清楚。

## 修复

1. 改**生成模板**（源头，taopm 的做法，patch 0002）：

   ```cpp
   #include <cmath>
   #include <iostream>
   #include "taodefs.h"
   ```

2. 消费者/自测代码：
   - 先 include 所有标准库头，再 include 库头；
   - 避免用 `min`/`max`/`samples`/`secs`/`Hz` 等词作标识符。
3. 包侧：`cpp_info.defines` 提供必需的平台宏（taopm 是 `TAO_NO_GRAPHICS`），
   让 `taodefs.h` 的图形分支在消费者侧也自动关闭。

## 验证

- 主机 MSVC `/std:c++17`：`taodefs.h` 在 STL 头之前 → 编译失败（vector(1877)）；
  调整顺序后编译通过（17 个 libtao 单元 + 3 个测试程序）。
- 真机：`conan create` + `test_package`（含 taoparse 生成的程序）全绿。
- 附带的 `#define samples` 重名问题在 `test_tao.cpp` 里以 `frames` 规避，
  已在该文件注释中说明。

## 适用面

老库若用"宏即单位"的方式做 DSL 语法糖（tao、部分 DSP/图形库），并且项目里有
代码生成器或示例代码先 include 库头，就应按此处理；`#define min/max` 这类
尤其危险，因为标准库实现普遍使用这些名字。
