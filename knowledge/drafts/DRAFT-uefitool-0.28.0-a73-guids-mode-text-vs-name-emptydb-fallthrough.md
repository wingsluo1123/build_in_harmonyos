# uefiextract 的 guids 子模式在 GUID 库为空时打印用法并退出 1

- **草稿 ID**: DRAFT-uefitool-0.28.0-a73-guids-mode-text-vs-name-emptydb-fallthrough
- **来源**: UEFITool 0.28.0-a73（上游 tag `A73`，new_engine 分支）适配
- **分类**: runtime / detection / upstream / cli / silent-failure
- **状态**: 本地草稿（未创建 Issue/PR，未生成知识编号，无审核结论）

## 问题 / 错误签名

参数**完全合法**，文件也成功读入并解析完，但工具打印用法文本并以 1 退出：

```
$ uefiextract probe.fv guids
parseFileHeader: invalid header checksum ...     # 与本条目无关，fixture 的告警
parse: not a single Volume Top File is found ... # 同上
UEFIExtract NE alpha 73 (Oct  4 2026)
Usage: UEFIExtract {-h | --help | -v | --version} - show help and/or version information.
       UEFIExtract imagefile guids  - only generate GUID database, no dump or report needed.
       ...
$ echo $?
1
$ ls probe.fv.guids.csv
probe.fv.guids.csv: No such file or directory
```

用法文本里明明写着 `UEFIExtract imagefile guids` 是受支持的形态，退出码 1 却又是
`U_INVALID_PARAMETER` —— 于是第一反应必然是"我的参数写法不对"，进而去反复试
`-m guids`、调换顺序、加 `-i`。**这条路是错的**，与参数毫无关系。

## 根因链（两处缺陷叠加）

### 环 1：收集函数取错了字段 —— 结果集恒空

`common/guiddatabase.cpp:111-128`：

```c
GuidDatabase guidDatabaseFromTreeRecursive(TreeModel * model, const UModelIndex index)
{
    GuidDatabase db;
    if (!index.isValid()) return db;
    for (int i = 0; i < model->rowCount(index); i++) {
        GuidDatabase tmpDb = guidDatabaseFromTreeRecursive(model, index.model()->index(i, index.column(), index));
        db.insert(tmpDb.begin(), tmpDb.end());
    }
    // ↓ 用的是 text
    if (model->type(index) == Types::File && !model->text(index).isEmpty())
        db[readUnaligned((const EFI_GUID*)model->header(index).left(16).constData())] = model->text(index);
    return db;
}
```

而 FFS 文件的**可读名**并不在 `text` 里：

- `common/ffsparser.cpp:2222`　`name = guidToUString(fileHeader->Name);`
- `common/ffsparser.cpp:2262`　`model->addItem(localOffset, Types::File, fileHeader->Type, name, text, info, ...)`

`addItem` 的形参序是 `（offset, type, subtype, `**`name`**`, `**`text`**`, info, …）`
（`common/treemodel.h:207-211`）。`text` 是独立的"短注记"字段，**只对特殊文件赋值**：

| 赋 text 的位置 | 值 |
|---|---|
| `ffsparser.cpp:2249` | `Volume Top File` |
| `ffsparser.cpp:2343-2351` | `NVAR store` / `NVRAM external defaults` / `NVAR BB defaults` |
| `ffsparser.cpp:2375` | `AMI ROM hole` |
| `ffsparser.cpp:3604-3624` | `PEI apriori file` / `DXE apriori file` |
| `ffsparser.cpp:4393-4516` | 各版本 `protected ranges hash file` |

⇒ 普通 FREEFORM 文件、DXE 驱动文件的 `text` 恒为空，**它们的 GUID 永远进不了这个库**。

同一个模型，`report` 走的是正确的字段（`common/ffsreport.cpp:66`：

```c
+ urepeated('-', level) + UString(" ") + model->name(index) + (text.isEmpty() ? UString() : UString(" | ") + text)
```

用的是 `model->name(index)`）—— 这就解释了为什么"报告里能看到 GUID，guids 模式却没有输出"。

### 环 2：该分支缺终结 return —— 落穿到用法文本

`UEFIExtract/uefiextract_main.cpp`：

```c
// 98-100：dump 分支，有 return
if (argc == 3 && !std::strcmp(argv[2], "dump")) {
    return (ffsDumper.dump(...) != U_SUCCESS);
}
// 101-107：guids 分支 —— 库为空时什么都不做，且没有 else
else if (argc == 3 && !std::strcmp(argv[2], "guids")) {
    GuidDatabase db = guidDatabaseFromTreeRecursive(&model, model.index(0, 0));
    if (!db.empty()) {
        return (int)guidDatabaseExportToFile(path + UString(".guids.csv"), db);
    }
}                                    // ← 空库时从这里掉出去
// 109-120：report 分支，空报告时有显式 return 1，成功时 return 0
else if (argc == 3 && !std::strcmp(argv[2], "report")) {
    ...
    return 1;                        // ← 对比：这个分支是有兜底的
}
...
// 216-218：函数尾部兜底
print_usage();
return 1;
```

一旦 `db.empty()` 成立，`if-else` 链被走完、没有任何分支接管，控制流直接落到函数尾部的
`print_usage(); return 1;`。**于是"库为空"被伪装成"参数错误"。**

### 附带的第三个现象：缺 VTF 会跳过整遍第二道解析

`common/ffsparser.cpp:103-109`：

```c
USTATUS result = performFirstPass(buffer, root);
if (result == U_SUCCESS) {
    if (lastVtf.isValid()) {
        result = performSecondPass(root);
    }
    else {
        msg(usprintf("%s: not a single Volume Top File is found, the image may be corrupted", __FUNCTION__));
    }
}
```

`lastVtf` 由文件 GUID 等于 `EFI_FFS_VOLUME_TOP_FILE_GUID` 时设置
（`ffsparser.cpp:2244-2249`、`2271-2273`）。没有 VTF 就整遍跳过 `performSecondPass()`
—— 后者做的是**地址侧分析**（reset vector / FIT / protected ranges / TE image base，
见 `ffsparser.cpp:3806-3835`），**不是**段解析。造测试镜像时值得知道这一点。

## 影响面

1. **直用者**：任何用 `uefiextract <img> guids` 拿 GUID 清单的脚本，在"镜像里没有
   特殊文件"时拿到的是用法文本 + 退出码 1，而不是"空清单"。
2. **间接受影响者（更隐蔽）**：`default`（`argc == 2`）与 `all` 模式也会顺带产出
   `.guids.csv`（`uefiextract_main.cpp:133-137`），但那里 `if (!db.empty())` 后面接着
   继续 dump，**不报错也不提示** ⇒ 拿到的是一个内容不全的 .guids.csv，比直接失败更难发现。
3. **同类实现（可迁移的教训）**：把模型的 A 字段当作 B 字段使用时，条件会恒不成立，
   表现为"结果集恒空"而非报错。同族判据见下。

## 最小修复（若要在上游修）

```c
// common/guiddatabase.cpp
if (model->type(index) == Types::File && !model->name(index).isEmpty())
    db[readUnaligned((const EFI_GUID*)model->header(index).left(16).constData())] = model->name(index);

// UEFIExtract/uefiextract_main.cpp（guids 分支补终结 return）
else if (argc == 3 && !std::strcmp(argv[2], "guids")) {
    GuidDatabase db = guidDatabaseFromTreeRecursive(&model, model.index(0, 0));
    if (!db.empty()) {
        return (int)guidDatabaseExportToFile(path + UString(".guids.csv"), db);
    }
    return U_ITEM_NOT_FOUND;         // 明确的"无内容可导出"，而不是伪装成参数错误
}
```

⚠️ 适配层**不要**私改上游源码来处理这个现象（P005/P011：这是可原样上游化的真缺陷）。
若随包必须带出，必须写成带完整元数据 header 的 `.patch` 并注明可上游化。

## 验证证据

UEFITool A73，**OHOS PC 真机**，两个独立信源结论一致：`conan create` 的
`test_package` 阶段（`test.sh` 的 C 层第 3 条断言），以及消费者用例之外的一次
手工复跑（同一 `make_fixture.py`，每次只改一个变量）。

| # | 输入 | 命令 | 实际结果 |
|---|---|---|---|
| 1 | fixture 只含一个 FREEFORM 探测文件（无 VTF） | `uefiextract probe.fv guids` | 打印用法、**rc=1**、不生成 `probe.fv.guids.csv` |
| 2 | 同一 fixture 追加一个 VTF（GUID `1BA0062E-C779-4582-8566-336AE8F78F09`） | `uefiextract probe.fv guids` | **rc=0**，生成 `probe.fv.guids.csv`（**53 字节**） |
| 3 | 在第 2 步镜像上把 VTF 的 GUID 抹掉（库再次为空） | `uefiextract novtf.fv guids` | **rc=1**，不产出文件（回到第 1 步形态） |
| 4 | 同第 2 步镜像，改走报告链路 | `uefiextract probe.fv report` | **rc=0**，同一节点显示为 `… -- SecCore_VolumeTopFile \| Volume Top File`（报告读 `name`，故有可读名） |

生成的 `.guids.csv` 内容：

```
1BA0062E-C779-4582-8566-336AE8F78F09,Volume Top File
```

★ **关键量化事实**：该镜像里**一共 2 个 FFS 文件**（FREEFORM 探测文件 `A1B2C3D4-…` +
VTF），而导出的 `.guids.csv` **只有 1 行** —— 普通文件被筛选条件**整类**漏掉，
这是环 1 的直接量化体现，而不是"排序/去重差异"那种可以解释掉的差别。
第 2 步与第 3 步之间只差 16 字节的 GUID，退出码就从 0 翻成 1，构成单变量对照。

## 可复用判据（速查）

1. **退出码与"参数校验"矛盾时**，先算一下"结果集是否可能为空"，再怀疑参数：
   `合法命令 + 打印用法 + rc=1` ⇒ 优先查收集函数，而不是查 CLI 语法。
2. **看到"报告里有、导出文件里没有"**，立刻对比两条链路用的是哪个字段
   （本例：report 用 `name`，guids 用 `text`）。
3. **反查筛选条件的恒真/恒假**：把条件里的字段构造一遍最小实例，数命中数；
   为 0 且没有报错 ⇒ 字段取错或条件写错，而不是"数据里确实没有"。
4. **空集合必须有独立出口**：`if (!x.empty()) { return f(x); }` 这种写法在空集合时
   没有任何返回，必须补 else/终结 return，否则会落穿到函数尾部兜底，
   把"没数据"伪装成"调用方用错了"。
5. **造 FFS2 测试镜像时必须放一个 Volume Top File**，否则上游连第二道解析都不跑
   （`ffsparser.cpp:103-109`）。

## 与其它条目的关系

- `similar_to`
  - **DRAFT-uefitool-0.28.0-a73-cli-contract-self-inconsistent** —— 同属"工具对外
    承诺的契约与实现不一致"。那一条讲帮助文本与实现不匹配（`-version` vs `--version`）
    与两个 CLI 无参数退出码不对称；本条讲"合法调用被报成参数错误"。
  - **DRAFT-uefitool-0.28.0-a73-guids-csv-gui-resource-only-cwd-lookup** —— 同一个
    `guids.csv` / GUID 名表子系统的另一面：那一条讲"名表文件没随包安装 + 按 CWD 查找
    ⇒ 静默退化成裸 GUID"；本条讲"GUID 收集取错字段 + 空库落穿 ⇒ 伪装成参数错误"。
    两条都会让"看名字"这件事失败，但失败面与修法完全不同，勿混为一谈。
- **与消费者的关系**：本条的断言同时钉住"fixture 必须含 VTF"这一前置条件，
  见 `test_package/make_fixture.py` 的模块说明与 `test_package/test.sh` 的 C 段注释。
