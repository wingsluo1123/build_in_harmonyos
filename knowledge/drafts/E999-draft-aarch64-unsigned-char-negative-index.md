# E999 draft — aarch64 `char` 无符号：`-1` 变成 255，索引越界

> 草稿条目（draft: true），待主编审核后提升为正式 E 编号。
> 结构化数据：[E999-draft-aarch64-unsigned-char-negative-index.kv](E999-draft-aarch64-unsigned-char-negative-index.kv)
> 发现来源：plast 2.3.2 在 HarmonyOS aarch64 真机上反向阅读框结果全错并段错误。

## 错误特征

小输入（结果静默错误，**没有任何报错**）：

```text
FRAME_4 got='EKKKKKKKKKKKKKKX' exp='LGFVKIMISYIVPSHX' MISMATCH
FRAME_5 got='KKKKKKKKKKKKKKKX' exp='SDL*RS*SHT*YLAIX'  MISMATCH
FRAME_6 got='KKKKKKKKKKKKKKK'  exp='RICKDHDLIHST*PL'  MISMATCH
```

大输入（同一个缺陷升级为崩溃）：

```text
Signal 11 (core dumped)
```

注意两者是**同一个根因**：先错，再崩。

## 触发条件

源码把一个“方向/符号”值用 **`char`** 承载并返回 -1：

```cpp
char getDirection()  { return (_frame==FRAME_1 || _frame==FRAME_2 || _frame==FRAME_3 ? 1 : -1); }
```

aarch64 上 `char` 无符号，`return -1` 得到的是 **255**；该值随后被提升为 `int 255`
参与算术并被当作数组下标：

```cpp
int direction = getDirection();              // 反向链时 direction == 255
... refData.letters.data[offset + direction*(i+2)] ...
```

于是索引直接飞到缓冲区之外：读到的字节是垃圾 → 密码子全部落进 `DEFAULT_CODE`
分支 → 翻译结果退化成同一个残基（本例全是 `K`）；缓冲区更大或写入路径上则触发 SIGSEGV。

**编译器不会报警**：窄化发生在 `return` 语句里，而不是在某次比较中，
所以 `-Wtautological-constant-out-of-range-compare` 抓不到它。

## 影响范围

- 任何把三态/方向/“未找到”哨兵塞进 `char` 的遗留 C/C++ 代码；
- 典型受害者：链方向、阅读框方向、查表键、“not found” 哨兵；
- 表现高度误导：**小数据集结果错误、大数据集崩溃**，很容易被当成数据问题或内存问题。

## 定位命令

```bash
# 1) 扫“用 char 返回 -1”的函数
grep -rn --include=*.c --include=*.cpp --include=*.h --include=*.hpp \
     -E 'char[[:space:]]+[A-Za-z_][A-Za-z0-9_]*[[:space:]]*\([^)]*\)[^;{]*\{[^}]*-[[:space:]]*1' .

# 2) 最小验证：同一个程序在 x86 返回 0，在 aarch64 返回 1
cat > /tmp/p.c <<'EOF'
static char f (void) { return -1; }
int main (void) { return ((int) f () == -1) ? 0 : 1; }
EOF
cc /tmp/p.c -o /tmp/p && /tmp/p ; echo "exit=$?"

# 3) 排查既有的“结果不对但没报错”的现象时，优先怀疑这类窄化
```

## 推荐方案（priority 1）

返回类型与局部变量都放宽为 `int`：

```diff
     /** Returns the direction of the current frame.
      * \return 1 for strands 1,2,3 and -1 for strands 4,5,6
+     *
+     * Note that the type is 'int' and not 'char': the value is used as an
+     * arithmetic operand (and as an array index offset) in udpateItem(), where
+     * a plain 'char' holding -1 is read as 255 on architectures where char is
+     * unsigned (arm64 for instance), which turns the indexing into an out of
+     * bounds access.
      */
-    char getDirection()  { return (_frame==misc::FRAME_1 || ... ? 1 : -1); }
+    int getDirection()  { return (_frame==misc::FRAME_1 || ... ? 1 : -1); }
```

```diff
-    char direction = getDirection();
+    int direction = getDirection();
```

实测案例：plast 2.3.2 `src/database/impl/ReadingFrameSequenceIterator.{hpp,cpp}`。
修复前 `testReadingFrameIterator` 断言失败、`testCompositeDatabase2` SIGSEGV；
修复后整轮单测 `OK (96 tests)`，反向阅读框（`plastx`/`tplastx`/`plastn` 的负链）结果恢复正确。

该补丁可向上游提交（P005）：`char` 承载 -1 在 C 标准里本就是实现定义行为，
改成 `int` 在任何平台都更正确。

## 回退方案（priority 2）

若返回类型受 ABI 约束无法改动，**不要**直接把该值用于算术/索引，而应显式符号扩展
或在正向/反向分支里各写一次索引表达式：

```cpp
int d = (signed char) raw;                        // 显式符号扩展
size_t idx = (d > 0) ? (offset + i + k) : (offset - i - k);   // 不依赖乘法
```

代价：改动面更大，且容易漏改；只建议在确实无法改签名时使用。

## ⛔ 禁止

```text
-fsigned-char / -funsigned-char     # 禁止：全局翻转 char 符号性
(int)(unsigned char) raw 当索引     # 禁止：把 255 强转后继续当索引用
assert(0 <= direction && direction <= 1) 后 clamp   # 禁止：只压住崩溃
```

理由：只 clamp 索引会让**崩溃消失但结果依旧错误**（小输入仍返回错误的负链翻译），
这比崩溃更危险——没有任何信号提示结果不可信。

## 关联

- **同类条目**：`E999-draft-aarch64-unsigned-char-eof-sentinel`
  （同一根因的另一种表现：EOF 哨兵失效 → 死循环）。两者错误特征与阶段不同，
  分别可独立匹配。
- **E419** — *Target plain-char signedness can change INT8 API results without changing
  stored bytes*：同根条目（plain char 符号性），E419 描述的是**取值语义**变化，
  本条目描述的是该取值被当作**数组下标**后的越界与崩溃，并给出「不得只 clamp 索引」
  的边界（clamp 后崩溃消失但结果依旧错误）。
- **同类草稿**：`DRAFT-8543-plain-char-eof-sentinel-infinite-loop` 与
  `E999-draft-aarch64-unsigned-char-eof-sentinel`（同一根因的另一种表现：EOF 哨兵失效
  导致死循环）。三者错误特征与阶段不同，分别可独立匹配。
- **P005** — 补丁必须可向上游提交
- **P013** — 平台限制必须降级而非绕过

---
*2026-10-15 · 来源：plast 2.3.2 适配（archives/p/plast/2.3.2/patches/0012-reading-frame-unsigned-char.patch）*
