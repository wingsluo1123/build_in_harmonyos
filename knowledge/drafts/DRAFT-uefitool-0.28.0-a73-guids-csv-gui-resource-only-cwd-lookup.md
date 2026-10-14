# 数据文件只进 GUI 的 Qt 资源、CLI 侧按 CWD 相对路径查找 —— 读失败静默降级成裸 GUID

- **草稿 ID**: DRAFT-uefitool-0.28.0-a73-guids-csv-gui-resource-only-cwd-lookup
- **来源**: UEFITool 0.28.0-a73（上游 tag `A73`，new_engine 分支）适配
- **分类**: packaging / runtime / conan / platform / detection
- **状态**: 本地草稿（未创建 Issue/PR，未生成知识编号，无审核结论）

## 问题 / 错误签名

**没有错误签名 —— 这正是本条目要沉淀的东西。**

剥离 GUI 后，两个 CLI 都能正常运行、退出码为 0、报告与 dump 照样产出。
唯一的差别是：报告里所有固件条目的名称都变成了裸十六进制 GUID 串，
而它们本该是可读名。

```
# 有数据文件时（期望）
Volume: EfiFirmwareFileSystem2Guid
File:   AprioriDxe

# 无数据文件时（实际，无任何提示）
Volume: 8C8CE578-8A3D-4F1C-9935-896185C32DD3
File:   1B45CC0A-156A-428A-AF62-49864DA0E6E6
```

可观察的"错误签名"只有那个**不该出现裸 GUID 的地方出现了裸 GUID**：

```
\b[0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12}\b
```

这只能靠**对照**发现，不能靠失败发现 —— 这是本条目与绝大多数条目最大的不同。

## 根因链（四环，每一环都不报错）

以上游 UEFITool 为例：

1. **数据文件的 install 归属错了**。GUID→可读名映射表（`common/guids.csv`，12042 行）
   只被 GUI 的 Qt 资源清单引用一次：

   ```xml
   <!-- UEFITool/uefitool.qrc -->
   <file alias="guids.csv">../common/guids.csv</file>
   ```

   两个 CLI 子工程的 `INSTALL()` 里**没有它**。它从来没有作为"CLI 的运行时数据"
   被安装过 —— 因为上游从没在无 GUI 的环境里跑过 CLI。

2. **查找路径是相对的**。`UEFIExtract` 的 `main()` **第一行**：

   ```cpp
   int main(int argc, char *argv[])
   {
       initGuidDatabase("guids.csv");        // 相对路径 ⇒ 按 CWD 解析
       if (argc <= 1) { print_usage(); return 1; }   // ← 晚于上一行
       ...
   ```

   注意它**早于** `argc` 检查 ⇒ 连 `uefiextract -v` 都会先去 CWD 找这个文件。
   CWD 里放了一份错误的表，会污染所有子命令的行为。

3. **加载失败是静默的**。`common/guiddatabase.cpp`：

   ```cpp
   static std::string readGuidDatabase(const UString &path) {
       std::ifstream guids(path.toLocal8Bit());      // 打开失败不检查
       std::stringstream ret;
       if (ret) ret << guids.rdbuf();                // 空流 ⇒ 空串
       return ret.str();
   }

   void initGuidDatabase(const UString & path, UINT32* numEntries)
   {
       gLocalGuidDatabase.clear();                   // clear 后填 0 条
       std::stringstream file(readGuidDatabase(path));
       while (!file.eof()) { ... }
   }
   ```

   **无 return 值、无异常、无日志、无退出码变化。**

4. **查表失败有回退格式**。`common/ffs.cpp`：

   ```cpp
   UString guidToUString(const EFI_GUID & guid, bool convertToString)
   {
       if (convertToString) {
           UString readableName = guidDatabaseLookup(guid);
           if (!readableName.isEmpty()) return readableName;
       }
       return usprintf("%08X-%04X-%04X-%02X%02X-%02X%02X%02X%02X%02X%02X", ...);
   }
   ```

   而声明 `common/ffs.h:25` 里 `convertToString` **默认为 true**
   ⇒ 卷名（`ffsparser.cpp:1520`）与文件名（`ffsparser.cpp:2222`）都走查表路径，
   查不到就回退成**大写带连字符的裸格式** —— 一种看起来完全"正常"的输出。

**四环叠加的后果**：功能实质上降级了，但在任何自动化门禁下都是绿的。

## 另有一处不对称值得注意

同包的另一个 CLI **完全不调用** `initGuidDatabase`：

```
$ grep -rn "initGuidDatabase" --include="*.cpp" .
./common/guiddatabase.cpp:53          ← 定义（宏开启）
./common/guiddatabase.cpp:97          ← 定义（宏关闭的空实现）
./UEFIExtract/uefiextract_main.cpp:51 ← 唯一的 CLI 调用点
./UEFITool/uefitool.cpp:141,1460,...  ← GUI 侧（用 ":/guids.csv" Qt 资源路径）
```

⇒ `UEFIFind` 从来就没有名表（它输出的是 item 路径，不需要名表）。

**所以"两个工具表现不一致"本身是定位线索**：一旦发现"同一个包里 A 工具的
输出有可读名、B 工具的没有"，先别怀疑解析器，先 grep 调用点。

## 最小修复方案

安装期把数据文件放到包的 `share/<pkg>/` 下：

```python
def package(self):
    cmake.install()
    copy(self, "guids.csv",
         src=os.path.join(self.source_folder, "common"),
         dst=os.path.join(self.package_folder, "share", "uefitool"))
```

消费侧在使用前把它放到工作目录（或显式传绝对路径）。

**为什么不把数据编进二进制**：上游选择的是"外部数据文件"这一设计
（GUI 用 Qt 资源、CLI 用文件路径）。在适配层改变装载方式会引入上游没有的
构建期代码生成步骤，并让此后上游的数据更新与适配层不同步。
装到 `share/` 是 conan 场景下的常规做法，且该函数本来就接受任意路径。

## 验证证据（关键：必须双向断言）

只验证"有数据文件时能读出名字"是**不够的** —— 那无法区分"该功能生效"与
"名字恰好来自别处"。必须用**同一份输入**跑两个方向：

```sh
# 方向一：CWD 无数据文件 ⇒ 必须是裸 GUID
( cd "$WORK" && uefiextract "$IMG" report )
norm < "$IMG.report.txt" | grep -q 8C8CE5788A3D4F1C9935896185C32DD3   # 裸格式

# 方向二：把随包安装的那份放进 CWD 后重跑 ⇒ 必须是可读名
cp "$PKG/share/uefitool/guids.csv" "$WORK/guids.csv"
( cd "$WORK" && uefiextract "$IMG" report )
grep -q EfiFirmwareFileSystem2Guid "$IMG.report.txt"                   # 可读名
```

锚点选**卷头**的 `FileSystemGuid`（本例 `8C8CE578-8A3D-4F1C-9935-896185C32DD3`
→ `EfiFirmwareFileSystem2Guid`），因为它必然出现在报告里、且必然在数据表中。

固定装置是自造的 4096 字节最小合法 FFS2 卷（纯标准库生成），
不依赖任何外部固件样本。

**方向二同时是"安装 `share/<pkg>/` 这一步是必要且有效的"的证明**
—— 这正是把"多装了一个文件"变成"可复现证据"的关键。

## 可复用判据（速查）

发现"适配后工具能跑但输出信息量变少"时，按顺序查：

1. `grep -rn "<数据文件名>" <src>/` —— 该数据文件被谁引用？
   若只在 `.qrc` / GUI 相关文件里出现，**大概率没被 CLI 侧安装**；
2. 找 CLI 侧的加载调用点，看路径是**绝对**还是**相对** —— 相对路径一律按
   CWD 解析，在包被安装后必然失配；
3. 看调用点是否早于参数检查（本例在 `main()` 第一行）—— 早于则连
   `--help` / `--version` 都会受影响；
4. 读加载函数的失败分支 —— 若无 return / 无 throw / 无日志，就是静默降级；
5. 找到最终格式化函数，确认失败时的**回退形态**（本例是大写带连字符的裸 GUID）,
   把它写成断言锚点。

## 与其它条目的关系

`principles: P013`（平台限制必须降级而非绕过）—— 本条的处置是"把数据按包规范
装到 `share/`"，属正向补全而非绕过。

同类形态的通用化：任何"**数据文件只挂在 GUI 侧资源、命令行侧用相对路径查找、
读失败静默**"的三元组，都适用本条目。典型候选：映射表、词典、规则表、
时区库、证书库、字体配置、模板目录。
