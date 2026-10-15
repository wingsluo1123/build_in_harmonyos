# DRAFT-mailx-8.1.2_git20220412-compiler-executables-fallback-path-error127
> tools.build:compiler_executables绝对路径缺失时回退PATH解决raw Makefile真机Error127
## 问题特征（真实日志片段/标记）
- 真机`conan create`在`build()`失败：`make: /data/service/hnp/bin/clang: No such file or directory`，随后`make Error 127`，配方`build()`第74行执行`make -j1 CC=配置值`。
- 门禁标记为`v2:compile:compiler_error`；修复轮attemptId 114546记录`progress: resolved`、`progressReason: 原问题已消失且真机门禁全部通过`、`gateOutcome: passed`，`resolved: [v2:compile:compiler_error]`、`remaining: []`、`new: []`。
- 配置来源：`ci/conan/profiles/ohos-aarch64: tools.build:compiler_executables={c: /data/service/hnp/bin/clang}`，为CI worker布局硬编码路径。
- HMBS_REPAIR_METHOD标题：`profile编译器绝对路径缺失时回退PATH解析`，关键词覆盖`compiler_executables`、`error 127`、`hmbs_repair_method`。
## 根因
- `ci/conan/profiles/ohos-aarch64`把`tools.build:compiler_executables`硬编码为CI worker布局`/data/service/hnp/bin/clang`，真机该路径不存在。
- mailx为raw Makefile配方，`build()`把conf值原样传给`make CC=`，不做存在性校验，触发`No such file or directory + Error 127`。
- 这是跨raw Makefile配方的通用模式，有`knowledge/drafts/DRAFT-9639` minibwa同症同因同解证据支撑。
## 修复方案（rec）（编号步骤，含具体文件与命令）
1. 在`archives/m/mailx/8.1.2_git20220412/conanfile.py`新增`import shutil`。
2. `build()`中将`tools.build:compiler_executables`取值改为`or {}`容错 + `(compilers.get(c) or clang).strip()`规范化，避免空值和首尾空格。
3. 对解析出的`cc`做`os.path.isfile(cc)`校验；路径存在时原样使用，保持CI语义不变。
4. 校验缺失时用`shutil.which(basename)`/`shutil.which("clang")`/`shutil.which("cc")`回退到PATH解析，并输出`warning+info`日志说明回退前后值，再传给`make -j1 CC=`。
5. 验证：工作树保持未提交等待HMBS自动真机预检；真机`conan create`通过且不再报`No such file or directory/Error 127`。本次PR另含`0001-Makefile.patch`至`0013-v7.local.c.patch`、`conandata.yml`、`manifest.yaml`、`notes.md`、`test_package/`等移植配套变更，编译器回退为其中Error 127专项。
## 禁止策略
- 禁止不做`isfile`校验直接把`tools.build:compiler_executables`绝对值透传给`make CC=`，即`CC=/data/service/hnp/bin/clang`写法。
- 原因：CI绝对路径在真机缺失必现Error 127；后果：真机`build()`失败，任务退回修复循环。
- 仅做存在性回退，不改变CI路径存在时的语义，不得改写profile或硬编码另一绝对路径替代。
## 与相近条目的边界（查重）
- 查重命中仅为`compiler error/compile_error/hmbs_repair_method`同词相邻条目，无`compiler_executables`路径回退主题覆盖，本条目增量明确。
- 相近条目处理通用编译失败定位，本条目专指CI profile绝对clang路径缺失致raw Makefile `Error 127`的`isfile+which`回退范式。
- 同症条目`DRAFT-9639 minibwa`为复用证据，不替代本条目；遇到相同签名时优先复用本rec。
## 适用判断
- 适用：直接读`tools.build:compiler_executables`并传给`make`/自定义构建的raw Makefile配方，且报错为`make: <绝对clang路径>: No such file or directory + Error 127`。
- 不适用：CMake/Autotools工具链自动解析编译器的配方，或缺失的是sysroot/头文件/库而非编译器可执行文件本身。
- 判定：先核对profile值是否为CI绝对路径且真机`isfile`为假，再执行回退；回退后仍找不到PATH编译器则按fallback保留审计日志。
