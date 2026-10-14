# 同一上游包内多个 CLI 的契约彼此不自洽 —— 消费者测试套统一模板必然误判

- **草稿 ID**: DRAFT-uefitool-0.28.0-a73-cli-contract-self-inconsistent
- **来源**: UEFITool 0.28.0-a73（上游 tag `A73`）消费者测试设计
- **分类**: testing / detection / compat / runtime / portability
- **状态**: 本地草稿（未创建 Issue/PR，未生成知识编号，无审核结论）

## 现象（两处不自洽，都无报错）

上游 `UEFITool` 发行版含多个 CLI 可执行文件（`UEFIExtract`、`UEFIFind`），
各自有独立的 `main()` 解析 argv，**没有共享的选项解析层**。于是：

### 不自洽一：帮助文本承诺的选项，实现不认

```
$ uefifind --help
UEFIFind NE alpha 73 (…)
Usage: UEFIFind {-h | --help | -v | -version}            ← 承诺 -version（单横线）
       UEFIFind imagefile {header | body | all} {list | count} pattern
       UEFIFind imagefile file patternsfile
```

而实现里是：

```cpp
else if (argc == 2) {
    UString arg = argv[1];
    if (arg == UString("-h") || arg == UString("--help")) {
        print_usage();
        return U_SUCCESS;
    }
    else if (arg == UString("-v") || arg == UString("--version")) {   // ← 只认 --version
        std::cout << PROGRAM_VERSION << std::endl;
        return U_SUCCESS;
    }
}
```

⇒ 照帮助文本敲 `uefifind -version`：既不等于 `-v` 也不等于 `--version`，
`argc == 2` 分支体执行完毕后落空，直接落到函数末尾的兜底：

```cpp
    print_usage();
    return U_INVALID_PARAMETER;      // = 1
}
```

**同包的另一个二进制没有这个问题** —— `uefiextract` 的 Usage 行写的是
`{-h | --help | -v | --version}`，与它的实现一致。**所以这不是"上游统一的小毛病"，
而是"同一份 Usage 格式被手工抄写成两份不同内容"的直接后果。**

### 不自洽二：「无参数」的退出码语义相反

```cpp
// uefiextract_main.cpp
if (argc <= 1) {
    print_usage();
    return 1;                 // ← 视为「用法错误」
}

// uefifind_main.cpp
if (argc == 1) {
    print_usage();
    return U_SUCCESS;         // ← 视为「打印帮助即成功」= 0
}
```

两者对"用户没给参数"这件事给出了**相反**的判断。

## 为什么危险：从"测试会挂"到"测试假绿"

危险程度是**递进**的：

1. **第一层（容易发现）**：写一个 `run_cli()` 模板套到所有二进制。
   若断言「无参数应返回非 0」，`uefifind` 挂；若断言「应对 0」，`uefiextract` 挂。
   测试失败，能看见 —— 但很容易被误判成"环境不稳"，然后被放宽掉。

2. **第二层（危险，最难发现）**：把「跑一下、`rc == 0` 即通过」当作"二进制可用"。
   此时如果参数变量展开为空（`$BIN` 未设置、路径拼错、`cd` 失败导致相对路径失效），
   `uefifind` 会走「无参数」分支 —— **打印帮助并返回 0**。
   测试全绿，而被测二进制**从未被正确调用过**。

   这属于最坏的一类测试缺陷：不是"测试挂了"，而是"**证据不实**"。
   它会把一个空壳验证伪装成一条通过记录。

3. **第三层（连带）**：`uefifind` 的「不命中」返回 8（`U_ITEM_NOT_FOUND`），
   而这在 shell 里是**非 0**。如果测试把"非 0"一律当作"执行失败"，
   那么"查不到东西"这个**正确的业务结果**会被误判为错误。

## 最小处置方案

**原则：以源码为准，不以帮助文本为准；逐个二进制分别钉住自己的契约。**

```sh
# 参数数量与模式：两个二进制各自断言（期望值不同，不要合并）
uefiextract              ; rc=$?   # 期望 1
uefifind                 ; rc=$?   # 期望 0
uefiextract -v / --help  ; rc=$?   # 期望 0
uefifind    -v / --help  ; rc=$?   # 期望 0
uefiextract /nonexistent ; rc=$?   # 期望 5（U_FILE_OPEN）
uefifind    /nonexistent ; rc=$?   # 期望 5
uefifind <img> bogus list 00 ; rc=$?  # 期望 1（U_INVALID_PARAMETER）
uefifind <img> body count <不存在> ; rc=$?  # 期望 8（U_ITEM_NOT_FOUND）
```

三条纪律：

1. **凡是从帮助文本推断出的期望值，先与源码核对再写入断言。**
   本例中"帮助文本承诺 `-version`"就是一条不能照抄进断言的线索。
2. **把「无参数退出码」当作被断言的契约之一**，不要假定它一定是非 0。
3. **对"帮助文本与实现不一致"这一项，记录事实但不写断言。**
   上游一旦修正（把 `-version` 改成认、或把 Usage 行改对），
   写死的断言就会变成**我们的**假失败 —— 那是在替上游的行为变更承担噪声。

   本包的做法：在 `test.sh` 的注释里写明这个不一致及其源码位置，
   断言只覆盖**稳定的、我们真正依赖**的契约。

## 适用边界

- 本条目主张的是**"如何为契约不自洽的多二进制包写消费者测试"**，
  **不主张**去修上游 —— 改帮助文本或统一退出码都是行为变更，属于上游的决定，
  适配层不应替它做。
- 反之，如果被交付的能力**依赖**某个特定退出码（例如上层脚本靠 `rc` 判断
  "是否命中"），那就必须把这个依赖显式写进测试并在文档里公示，
  因为它是一条**跨版本脆弱**的约定。

## 可复用判据（速查）

拿到一个含多个可执行文件的包，写消费者测试之前先做四件事：

1. 列出包里所有二进制（install 规则 / `bin/`）；
2. `grep` 每个二进制的 Usage/帮助文本原文；
3. `grep` 每个二进制 `main()` 里**所有** `return` 及其所在分支，逐条与帮助文本对照；
4. 用同一组输入（`-h` / `--help` / `-v` / `--version` / 无参数 / 缺文件 /
   非法模式 / 检索不命中）实跑每个二进制并记录退出码，与第 3 步的静态结论对照。

第 3 步与第 4 步的**差异**就是不自洽之处；第 4 步里"非 0 但属于正常业务结果"
的那些（如"检索不命中"）是最容易被误判成失败的东西。
