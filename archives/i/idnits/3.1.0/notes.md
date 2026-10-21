# idnits 3.1.0 HarmonyOS PC 适配说明

## 软件说明

idnits 是 IETF 官方工具链中的 Internet-Draft / RFC 规范检查器，用于检查
nits（小瑕疵）、引用下溯（downref）、版权年份、关键字大小写、XML/TXT 解析等
合规项。3.x 系列是 ietf-tools 维护的 Node.js (ESM) 重写版，纯 JavaScript、
无 native addon，运行时只需系统 Node.js（upstream engines 要求 >= 20）。

## 适配方式

- 源码归档：GitHub 官方 tag `3.1.0` 的 tar.gz
  （SHA256 `80a60387bac954fbbd1a4e1099492bfc2eba081b7776ecf7fadf11ba2dafed85`），
  优于 npm 发布包：GitHub tag 归档包含完整 `tests/`。
- 无构建步骤：tag 内已提交构建产物 `lib/`（ESM），配方只负责安装 9 个纯 JS
  生产依赖并打包 `cli.js + lib + node_modules + package.json`。
- 源码 URL/SHA256 声明在 `conandata.yml`（G1 门禁要求），配方通过
  `self.conan_data["sources"]` 读取；无 patches。若 CI 的 conandata
  pre-download 路径触发 `BUILD_DIR: parameter not set` 基础设施缺陷，再按
  xmodem 先例回退为配方内固定元数据并删除 conandata.yml。
- 启动器 `bin/idnits`：PATH 前置设备 node 目录（`IDNITS_NODE_DIR` 可覆盖，
  默认 hnp node_v24.13.0）+ `node --jitless`。不要用 `env -i`：完全清洁的
  环境会破坏 OHOS 的 exec 权限检查（真机实测 `node: inaccessible or not
  found`），继承 conan 会话环境运行 node 正常（r2 构建冒烟实测）。

## W0 依赖结论

- 运行时依赖 9 个（package.json dependencies，全部纯 JS，无 native addon）：
  chalk@5.6.2、entities@7.0.0、fast-xml-parser@5.2.5、jschardet@3.0.0、
  listr2@9.0.4、lodash-es@4.17.21、luxon@3.7.2、semver@7.7.2、yargs@18.0.0。
  均由配方在 build 阶段 `npm install --omit=dev` 安装，不拆分独立 Conan 包。
- 构建/测试依赖（devDependencies：vitest、eslint、msw 等）不进入包产物，
  不声明为运行时依赖。
- 无 Conan 图依赖（`build.dependencies: []`）。

## 上游测试说明

- 上游共 13 个 Vitest 测试文件、590 个测试用例。
- 本机（Windows 构建宿主，Node v24.9.0，Vitest 3.2.4）：587/590 通过。
- 3 个失败全部位于 `tests/metadata.test.js`（如 "date in the future"），
  报错为 `Error: Invalid unit value 十月`：宿主机 zh-CN locale 下 luxon 的
  月份名解析失败，属宿主 locale 环境问题而非代码问题（已验证：设置
  LANG/LC_ALL 在 Windows 上无效；POSIX/en locale 预期通过）。未修改、未跳过
  任何上游测试源码。
- **真机上游测试（已穷尽方案，判定为平台硬限制）**：在设备构建工作区安装
  actions-up 同款测试栈 vitest@4.1.9 + vite@7.3.6 + msw + @rollup/wasm-node
  后逐级验证，两条路径均被平台阻断：
  1. 不带 `--jitless` 运行 node → V8 `Check failed: 12 ==
     (*__errno_location())`，Signal 5 (core dumped)；
  2. 带 `--jitless`（jitless 强制，见下）→ WebAssembly 被禁用，而 rollup
     原生构建不支持 openharmony/arm64（vitest → vite → rollup 必经），唯一
     替代 `@rollup/wasm-node` 初始化即抛 `ReferenceError: WebAssembly is not
     defined`。
  与 ts/10.9.2（ava 矩阵）同一"二选一"口径：无 jitless 即 Signal 5，jitless
  下 rollup wasm 链不可用。按"具体报错定位 + 排除缺依赖"口径申报。
- 真机 shadow CI（r4，exit 0）已验证：conan create（含 npm 安装 9 个生产
  依赖、构建期 CLI 冒烟）、L0/L1/L1e/L4/L5 全 pass、test_package 4/4。

## test_package

4 项消费者侧断言（`test_idnits.sh`）：

1. 启动器 `idnits` 在 Conan Runtime Environment 中可见；
2. `idnits --version` 输出为合法 semver 字符串（注：上游 tag 3.1.0 的
   package.json version 字段仍是 "3.0.0"，CLI 打印 3.0.0，为上游已知滞后，
   故断言 semver 格式而不伪造版本号）；
3. 对打包内置的 `draft-smoke.txt` 做一次真实离线 nit-check（fixture 有意保留
   nits，idnits 可能以非零退出，断言只针对报告输出含 idnits 横幅）；
4. 错误路径：不存在的文件必须被拒绝（本机验证 exit 1）。

## 本机验证记录

- 上游测试：587/590（3 个 locale 失败已归因，见上）。
- CLI 冒烟：`node cli.js --version`、`node cli.js <fixture>` 均正常。
- 配方逻辑：source URL/SHA256 复核一致；依赖清单与上游 package.json 一致；
  Python 语法检查通过；改动范围仅 `archives/i/idnits/`。
- Windows 宿主上的 `conan create` + test_package（`/system/bin/sh`）不可执行，
  按仓库惯例以 Git Bash 等价验证 + 真机 shadow CI 兜底。

## 验证命令

`python3 scripts/ohc-run.py conan-verify idnits 3.1.0`

## 真机 shadow CI 结果（r1–r4）

隔离 job 单包排队执行（全局锁，wait_seconds=0，r4）：

| 轮次 | exit | 结果 |
|---|---|---|
| r1 | 1 | validate() 在设备 PATH 找不到 node → 增加 hnp node 路径解析 |
| r2 | 1 | 构建冒烟全过；test_package 直接 exec launcher 被 HMDFS 拒绝（126） |
| r3 | 1 | 复制到 el2/cache 后直接 exec 仍被拒；`env -i` 反而破坏 exec 权限上下文 |
| r4 | **0** | launcher 经 `sh` 显式执行 + PATH 前置 node + jitless；**L0/L1/L1e/L4/L5 全 pass，L2 skip（非阻塞通用探针），test_package 4/4** |

- L1e：`Negative test confirmed — test genuinely depends on idnits`。
- L2 的 skip 为 CI 通用 semver.js 探针不适用（非本包 bin 问题，bin/ 实际可用，
  test_package 已真实执行 launcher）。
