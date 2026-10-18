# OHOS HMDFS conan 缓存文件级完整性治理（签名失效拒载 / 原地覆盖 EPERM / 幻影条目 / 烙死路径 / 相对 NEEDED）

> 知识库拓展四件套（检测 / 策略 / 文档 / 样例）。来源：kturtle 26.04.0 适配期间
> 的多轮对照实验（含 os.open 创建 / 原地 r+b 改写 / 逐字节复制 vs 翻转一字节
> 的决定性对比）+ 29 包 × 2 轮全量重下实证。所有结论均在本机逐条实测复验。

## 一、问题定义（何时怀疑命中本套件）

满足以下任一场景，且报错形态为「动态库/可执行文件无法加载（Permission
denied）或符号断链」，即用 ① 检测脚本体检：

- 已发布包的 `.so` 加载报 `Error loading shared library ...: Permission
  denied`，而 `ls -l` 权限位正常、事后 chmod 无效；
- 用 patchelf / python / tar 等工具**改写过**某个已签名 `.so` 的内容，改完
  立刻不能加载；
- 同一文件反复出现/消失，`find` 能列出、`cat` 读不出（幻影）；
- 发布件报 `.../.cache/conan2/p/<pkgid>/p/lib/libX.so: No such file or
  directory`（构建 worker 的缓存布局路径被烙进 DT_NEEDED，本机不存在）；
- test_package 报相对 NEEDED 断链（`../../bin/libX.so` needed by ...）。

## 二、实测规律（平台真理，均已验证）

| # | 规律 | 实验证据 |
|---|------|---------|
| R1 | **exec/mmap 装载以 `.codesign` 签名有效性为准绳**：对已签名 ELF（CI 发布件带 .codesign 段，`readelf -S` 可见）做**逐字节原样复制**后可正常进入装载流程；**翻转任意 1 字节**后 dlopen 立即 `Permission denied`。此前盛行的「创建方式/权限位决定 exec」假说被同批实验否定 | 决定性对比：同一新鲜签名件，T1 逐字节复制（os.open 创建、mode 770）→ 报「缺依赖」而非拒载；T2 仅 0x200 一字节异或 → Permission denied |
| R2 | **无签名 ELF 不受 R1 约束**：新编译的最小 .so 无论以 python 写(660+chmod)、os.open(770)、tar 解包、cp 哪种方式落盘均可加载——mode 位与创建方式都不是判据 | reproduce.sh 无签名矩阵：S1/S2/S3 全 PASS |
| R3 | **HMDFS 拒绝对已存在文件原地覆盖写**（EPERM）：`cp f f` / 重定向覆盖报 `Operation not permitted`，必须 `rm -f` 后再落新文件 | reproduce.sh R3 段实测；与 knowledge/drafts/signed-elf-overwrite-eperm.kv（写侧保护）互为印证 |
| R4 | **幻影条目**：`-f`/`find` 可见但读失败（目录项与数据块不一致）。任何 rm/cp 前必须先 `cat src>/dev/null` 验证源真实可读，否则会把好目标 rm 成空洞 | walk 修复脚本 `cp: bad '...': No such file` 序列 |
| R5 | **发布件烙死构建 worker 的缓存布局**：KF6/Qt 发布二进制的 DT_NEEDED 含绝对路径 `~/.cache/conan2/p/<pkgid>/p/lib/...`；**绝对 NEEDED 解析优先于 LD_LIBRARY_PATH**——该路径必须真实存在 | readelf -d 实测 + 断链加载日志 |
| R6 | **相对 NEEDED 按 CWD 解析**：`../../bin/libX.so` 由动态加载器按**当前工作目录**拼路径，与 LD_LIBRARY_PATH 无关 | conan test() CWD 对照 |
| R7 | **CONAN_HOME 隔离会整体脱离 R5 烙死路径**；缓存清理中断（rm -rf 半途被杀）造成 conan DB 与磁盘不一致，后续 `os.utime: No such file` 连环报 | 隔离 CONAN_HOME 全程对照 |

**推论（修复设计的根）**：
- 一切「让发布件重新可加载」的手段，本质都是**把原字节原样放回**（rm+cp、
  conan remove+download 重下、tar 解包）——不是恢复什么「权限位/属性」；
- **禁止对已签名库做任何内容级修补**（patchelf 改 NEEDED、python 二进制替换
  字符串等一律使签名失效）；相对 NEEDED 必须用**不改字节**的 cwdroot 方案；
- 终版收敛：依赖装回**默认缓存**（烙死路径所在）且全部 conan 自建，kturtle
  conan-verify 全绿（全新编译 + test_package 真实执行通过）。

## 三、处理策略（② 修复脚本实现的三类处置）

1. **签名失效拒载（R1）/ 幻影（R4）** → 内容级修补不可逆，唯一出路是恢复
   原始字节：`conan remove <pkg> -c && conan download <pkg> -r=<remote>`（脚本
   `plan` 子命令生成清单；删除动作留给操作者）。
2. **断链绝对 NEEDED（R5）** → 从可信源做**逐字节**填充：候选源先读验证
   （R4 防空洞），`rm -f` 后 `cp`（R3 禁原地覆盖）。脚本 `fill` 子命令。
3. **相对 NEEDED（R6）** → **不改字节**的 cwdroot 方案：test_package 在
   test() 里把基名库硬链/cp 进 `<parent(build)>/bin`，chdir 到
   `<build>/cwdroot` 运行。参考实现：`../test_package/conanfile.py` 的
   cwdroot 段（本机 HMDFS 硬链不可用时回退 `/bin/cp`，CI ext4 上走
   shutil.copyfile——三环境兼容）。

## 四、使用方法

```sh
# 1. 体检（缺省扫 ~/.cache/conan2/p；隔离缓存传 "$CONAN_HOME/p"）
sh detect-hmdfs-exec-integrity.sh                       # 报告落 <缓存>/.cache-audit.txt
sh detect-hmdfs-exec-integrity.sh /path/to/conan2/p /tmp/audit.txt

# 2. 拒载/幻影病灶 → 重建清单（含受影响包目录统计）
sh repair-hmdfs-cache.sh plan /tmp/audit.txt

# 3. 断链病灶 → 逐字节填充（第 4 参数为可信新缓存，缺省同旧缓存）
sh repair-hmdfs-cache.sh fill ~/.cache/conan2/p /tmp/audit.txt ~/.cache/conan2/p

# 4. 复检退出码为 0 即干净
sh detect-hmdfs-exec-integrity.sh /path/to/conan2/p /tmp/audit2.txt
```

## 五、限制

- 检测对大缓存是 O(N) 单趟扫描（只扫 `*.so*` 与 `bin/` 文件；幻影检测限定
  同类文件，全树 cat 扫描代价过高）；
- **签名有效性只能间接检测**：本套件用「A 类咨询项」（ELF 无 owner-x 位，
  与被改写史强相关）+「C 类断链」定位问题文件，无法离线验证 .codesign 的
  密码学有效性——最终判据是加载时的 Permission denied；
- readelf 取 `/data/service/hnp/bin/clang` 同目录或 PATH 中的实现；无 readelf
  的环境 C/D 两类不适用（exit 2 提示）；
- `plan` 输出的包目录名是 pkgid 哈希，reference 对应需操作者 `conan list`
  核对（不做哈希反查，避免假设 conan 元数据完好）；
- R1/R3 在 HMDFS（/storage、$HOME）实测成立；ext4/CI worker 无签名强制，
  本套件脚本在 CI 上应零命中、透明无害。

## 六、复现（样例演示库）

`reproduce.sh` 两阶段复现（日志全部落文件，无管道 head，规避 SIGPIPE）：

- **阶段 1（自包含，无需网络）**：最小 C 库以 tar 解包(770)/python 写+chmod/
  cp 三种方式落盘并逐个 dlopen——**预期全 PASS**（无签名件不受 R1 约束，
  证伪「创建方式/mode 位」假说）；随后演示 R3：原地覆盖 EPERM、rm+cp 成功。
- **阶段 2（需一个已签名发布件，脚本自动 `conan download` 一个 KF6 库；
  无 conan 环境时传 `--signed <so路径>` 跳过）**：逐字节复制 → 加载推进
  （报缺依赖，非拒载）；翻转 1 字节 → Permission denied。对照即 R1 实证。

```sh
sh reproduce.sh /tmp/hmdfs-demo            # 全程自动
cat /tmp/hmdfs-demo/result.txt             # 矩阵 + 断言结论
```

## 七、适用范围

- 库/应用类型：所有经 conan 分发 OHOS aarch64 二进制制品的包（实证载体为
  KF6 全家桶 + qtbase 依赖图，29 包）；
- 平台：HarmonyOS PC 开发机（HMDFS）；CI（ext4）不触发本病灶；
- 关联知识图谱：已签 ELF 原位覆盖 EPERM 草稿
 （knowledge/drafts/signed-elf-overwrite-eperm.kv，R3 写侧特例）、E046
  （chmod 不生效——R1 早期假说的成因之一）、harmonyos-specifics.md §chmod。
