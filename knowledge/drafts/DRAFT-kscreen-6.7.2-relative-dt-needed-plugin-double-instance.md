# DRAFT-kscreen-6.7.2: 依赖包插件的构建树相对 DT_NEEDED —— 消费者按 CWD 字面解析、错副本即双实例、静默转型失败

> 一类问题：**已发布依赖包**里的运行期插件携带**构建树相对**的 `DT_NEEDED` 条目。消费者进程
> 装载该插件时，装载器把相对串当字面路径、按**消费者自己的 CWD** 解析——落点缺失则 dlopen 失败；
> 落点恰有无关同名副本则"同库两份实例"，插件对象的类型转型静默失败。两种失败在行内被归并成
> **同一条误导性错误串**。来源：OHOS PC 上 kscreen 6.7.2 适配（消费 libkscreen/6.7.2@ohpcd），
> 真机干净重建下实证修复。结论与具体库、具体语言无关，凡"无 SONAME 库按相对路径入链并被插件承载"
> 的已发布制品都适用。

## 症状

上游测试套件（QTest，10 个测试函数）在真机上 **0/10 全挂**，且每个用例的失败输出只有一行：

```
Plugin does not provide valid KScreen backend
```

末了进程以 SIGSEGV 收尾。表象看起来像"环境里没有后端插件/依赖装缺了"，但：

- 插件文件明明在包里（`lib/plugins/kf6/kscreen/KSC_Fake.so` 存在）；
- `QT_PLUGIN_PATH`、offscreen QPA、依赖库目录都已按常规注入；
- 同一批用法在别的依赖组合下都能装起来。

也就是说：**"插件找到了"与"插件不可用"同时成立**——这是本模式最容易把人带偏的地方。

## 根因

### 一枚被烙进已发布二进制的相对路径

```
llvm-readelf -d <libkscreen包>/lib/plugins/kf6/kscreen/KSC_Fake.so | grep NEEDED
  (NEEDED)  Shared library: [../../bin/libKF6Screen.so]      ← 罪魁：构建树相对条目
```

相对条目的来历：该插件在依赖包自己的构建树里链接时，`libKF6Screen.so` 这条被链接库**没有
SONAME**，链接器于是把链接命令行上给出的路径**原样**写进 `DT_NEEDED`——这里恰好是一条相对
路径（`<插件构建目录>/../../bin/libKF6Screen.so` 的标准构建树布局）。制品打包后，这条相对
字符串继续留在已发布二进制里。

### 装载器对相对条目的解析规则

含 `/` 的 `DT_NEEDED` 条目是**字面路径**：装载器不查 `LD_LIBRARY_PATH`、不查 `rpath/RUNPATH`、
不查任何搜索目录，直接以该字符串为目标 `open()`。相对字符串因此按**当前进程的 CWD** 解析。

关键点：现在的"当前进程"是**消费者**（kscreen 的上游测试 `osdactions`，由 ctest 从
`<build>/tests` 启动），不是依赖包自己。于是 `../../bin/libKF6Screen.so` 的落点变成
`<build>/../bin/libKF6Screen.so`——消费者构建树旁边的位置，与依赖包的安装布局毫无关系。

### 两个失败分支（殊途同归）

```
                       消费者进程 CWD = <build>/tests
                       插件 NEEDED = "../../bin/libKF6Screen.so"
                                   │  字面解析（不走搜索路径）
                    ┌──────────────┴──────────────┐
             落点无文件                      落点有无关同名副本
                    │                              │
        插件 dlopen 失败                   装着装着给插件绑定了
        （instance == nullptr）           第二份 libKF6Screen.so
                    │                              │
        loader->errorString()        QPluginLoader 返回的实例
                    │                qobject_cast<KScreen::AbstractBackend*>
                    │                失败（QMetaObject 链地址来自两份拷贝，
                    │                 对不上：libkscreen backendmanager.cpp:198
                    │                 else 分支）
                    └──────────────┬──────────────┘
                                   ▼
              下游归并为同一条错误串（libkscreen src/configoperation.cpp:126）：
              const QString &e = QStringLiteral("Plugin does not provide valid KScreen backend");
              q->setError(e);   // ←—— 测试输出里唯一能看到的失败原因
```

- **缺失分支**：典型表现在 `QPluginLoader::errorString()`（"Error loading shared library
  ../../bin/libKF6Screen.so ..."）。
- **错副本分支**：**没有任何装载层报错**——插件"装上了"，返回的对象也在，只是转型失败。
  此时进程里已经有两份 `libKF6Screen.so`（主程序经 `LD_LIBRARY_PATH` 装载一份，插件经字面
  相对路径装载第二份），Qt 的 `qobject_cast` 基于 `QMetaObject` 链地址比较，插件的
  `Fake` 类继承自"另一份" `KScreen::AbstractBackend`，转型必然失败。

两个分支在下游被归并成同一错误串的写法（`setError` 只区分"backend == nullptr"），这就是
"明知插件在包里却说 backend 不合法"的全部原因。**误判成缺依赖/缺插件会一路修错方向。**

## 最小定位过程（可复制）

1. **双端 `readelf` 对照**——把"插件端的 NEEDED"和"主程序端的 NEEDED"都打出来：

   ```
   llvm-readelf -d <依赖包>/lib/plugins/kf6/kscreen/KSC_Fake.so | grep -E "NEEDED|SONAME|RPATH|RUNPATH"
   llvm-readelf -d <消费者构建树>/tests/osdactions        | grep -E "NEEDED|SONAME|RPATH|RUNPATH"
   ```

   插件端出现相对串、主程序端是裸库名（或另一条路径）——两端**解析落点不同**即命中本模式。

2. **打开 Qt 类别调试，露出真实分支**——真实失败点被 `qCDebug` 藏着，把类别打开：

   ```
   QT_LOGGING_RULES="org.kde.kscreen*=true" ctest --test-dir <build> --output-on-failure
   ```

   （Qt 类别实名是 `org.kde.kscreen`；`kscreen*=true` 这种"以为的前缀"是无效的，什么都不
   会打。）看到 `... does not provide valid KScreen backend` 来自 `backendmanager.cpp:198`
   即"转型失败"分支——证明插件装载成功了、问题在解析落点。

3. **独立进程的 dlopen 矩阵**——不要在同一个进程里试（已加载对象会污染结论）。起独立
   ctypes 进程逐一探测：把 CWD、相对布局分别摆在不同组合（中性 CWD / 相对布局已物化 /
   主程序侧路径首位的相对目录），确认"字面解析 + CWD"语义与"两侧须同一文件"的收敛条件。

4. ctest 的启动目录（测试进程 CWD）可从 `<build>/CTestTestfile.cmake` 的
   `set_tests_properties(... WORKING_DIRECTORY ...)` 读出——它就是相对串的解析基准。

## 修复（消费者侧收敛两条解析链）

**唯一正确方向：让主程序与插件解析到同一字面路径字符串、同一文件。**

```
① 物化相对布局：把 <build>/../bin/libKF6Screen.so 以「普通文件复制」放到位
   - OHOS 用户卷拒绝 symlink()/link()（实测 EPERM/EACCES），CMake 的链接别名手段不可用；
   - 覆盖已存在文件同样被拒（O_TRUNC EPERM）→ 用 exists 守卫保持幂等。

② 相对目录进 LD_LIBRARY_PATH 最左：conan Environment 里最后一次 prepend 的值在最左
   test_env.prepend_path("LD_LIBRARY_PATH", "../../bin")
   → 主程序的裸名 "libKF6Screen.so" NEEDED 命中的是同一条字面路径字符串
   → 装载器判为同一装载对象（同一相对串、同一 CWD 打开同一文件）：全进程单实例（真机实测）。
```

配方落地即 `_stage_relative_backend_layout()`（物化）+ 测试环境注入（首位相对目录）两处
**协同**，缺一不可：

- 只物化副本、主程序仍走绝对路径加载 ⇒ 双实例仍在（只是从"缺失"分支换到"转型失败"分支）；
- 只把相对目录进 LD、不做物化 ⇒ 主程序换了装载对象、插件仍找不到落点（反之亦然）。

### 反例 / 常见错误做法

| 做法 | 结果 |
|---|---|
| 把无关副本放进落点就收工 | 双实例仍在，静默转型失败原样出现 |
| 只调 cwd / 只拷副本（二者做一） | 两端仍不收敛，失败分支平移 |
| 在依赖包缓存里改布局（塞文件/改包内二进制） | 不可复现、违反"不改已发布包"的纪律；重装即失效 |
| 用 patchelf 改插件 NEEDED | OHOS 内核对改写后的 `.so` 拒绝装载（E537 / DRAFT-13577 已记录的同类边界） |

### 根治方向（长期）

生产者侧重链：依赖包以带 SONAME 的方式链接（`-Wl,-soname,...` 或 `-l:` 重链）后，相对串
不会再进 `DT_NEEDED`。消费者修的是"落点收敛"，生产者修的是"不生相对串"——两者不冲突。

## 与相邻条目的边界

| 条目 | 焦点 | 与本条目的关系 |
|---|---|---|
| E537 | `DT_NEEDED` 记**绝对** conan 缓存路径 → 干净机装载失败；修=链接期 SONAME/`-l:` 重链 | 绝对版对照组：绝对串在任何 CWD 都是同一固定位置；相对串的落点**随消费者 CWD 漂移** |
| DRAFT-13577 | 陈旧**绝对**路径的按路径重建（symlink 到依赖图真实库） | 同为"装载期修复"，但对象是绝对条目；相对条目的落点漂移使其不可直接套用 |
| bctoolbox 5.3.115 知识 #13 | 含 `/` 的 `DT_NEEDED` 按 CWD 字面解析规则（**自家** tester：换个 cwd 即可） | 同一条装载规则的先行记录；本条目的增量=对象是**消费者无法改的已发布包插件**，cwd 无处可调，必须"物化 + 同路径收敛" |
| E492 / E330 | 无 SONAME 时共享库别名的物化/关闭版本化别名 | 物化手法同源（普通文件复制），场景不同（构建产物别名 vs 已发布插件的相对条目） |

## 验证记录（真机，2026-10-15）

环境：HarmonyOS PC（aarch64-linux-ohos，musl）；kscreen 6.7.2 配方 + 已发布
libkscreen/6.7.2@ohpcd；`conan remove` 后**全量干净重建**（消除缓存假绿）。

- 修复前：`osdactions` 10 个测试函数 **0/10** 全挂、SIGSEGV 收尾（统一错误串见上）。
- 修复后（同二进制、同测试环境，仅配方物化+环境注入）：

```
1/1 Test #1: osdactions ....................... Passed  0.14 sec
100% tests passed, 0 tests failed out of 1
Totals: 12 passed, 0 failed, 0 skipped        ← 函数级（10 个测试函数 + init/cleanup）
```

- 随档：`archives/k/kscreen/6.7.2/reports/conan-create.log`（ctest 段 L1286-1295）、
  `reports/conan-verify-report.md`（八门禁 Verdict PASS）。

## 复用清单（命中即取）

- 消费者测试/应用 **加载已发布依赖包的插件**（QPluginLoader / dlopen / 插件框架）时出现
  "插件在、却报不可用"的静默失败；
- 依赖包代码里能定位到**无 SONAME** 的被链接库，且插件 `DT_NEEDED` 里出现相对串条目；
- 修复动作固定两步：**物化相对落点（普通文件复制 + 幂等守卫）＋ 相对目录置
  `LD_LIBRARY_PATH` 最左**——保证主程序与插件收敛到同一文件、单实例。
