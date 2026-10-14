- **三方库名称**：sratom（LV2 Atom ↔ Turtle RDF 序列化库，drobilla/lv2 生态）
- **上游版本**：0.6.22
- **上游仓库地址**：https://download.drobilla.net/sratom-0.6.22.tar.xz（sha256 0209b7d0...，drobilla 官方发布源）
- **适配路径**：路径 A（基础适配）
- **使用知识库**：openharmony-compile-agent（依赖图钉版互斥同族解法 + pkg-config 两步法实证）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 2 | test/meson.build 注册（suite=unit）：trip / write（共享 forge_test_object.c / test_uri_map.c 夹具） |
| 头文件探针 | 1 | test/headers/test_headers（编译期警告探针，非断言型，单列） |
| **合计** | **2**（+1 探针） | 清点证据见 reports/test-report.md §一 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 2 | 不变 | trip / write 全部保留（配方 -Dtests=disabled 保持库配方纯净，实跑走离线三步法） |
| 鸿蒙特有测试 | 1 | 新增 | test_package/test_sratom_roundtrip.c：链接包内 libsratom-0，forge→sratom_to_turtle→sratom_from_turtle 逐字段断言往返一致性（真实数据链路，非纯断言） |
| **合计** | **3** | **+1** | 上游 2 全部保留实跑 + 鸿蒙特有 1 |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例（探索期零源码修改，`diff -rq` 证实，conandata.yml 无 patches 声明）
- 上游测试未挂进配方常规构建（-Dtests=disabled），实跑为离线三步法逐用例执行

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有 2 个注册单元测试（trip/write），新增 1 项鸿蒙特有消费者测试：Int32 原子往返 body 字节级全等；Object 原子属性数/label String 字段无损/x 属性经 sratom 的 xsd:int 映射回读 atom:Int 2026（实测字节 EA 07 00 00 证据，上游设计行为 test_write.c 注释印证）

## 验证结果

- 编译状态：**通过** — conan create 干净构建成功（libsratom-0.a，OHOS aarch64）；conan-verify G1/G2/G3 + L2/L4/L5 全绿
- 上游测试用例通过率：**2/2（100%）** — trip 输出 "All tests passed."（glib testing 全绿）、write rc=0（上游设计的警告路径验证）、headers 探针 rc=0，逐用例证据见 reports/test-report.md §二
- 验证命令与结果：`conan create` → test_package 输出 `INFO: x round-trip: Int 2026 / PASS: sratom consumer test`；`conan-verify` → `✅ 配方验证通过: sratom 0.6.22`
- 新增测试用例通过率：**1/1（100%）**
- 依赖：sord/0.16.22 + lv2/1.18.11-git（制品仓已发布；不显式钉 serd——sord 传递钉 serd/0.32.9，显式钉版冲突实证见 notes.md）

## 补充说明

1. 本包为 jalv 1.10.0 适配的依赖前置（R36 拓扑序：sratom → lilv → jalv），lilv/jalv 后续 PR 引用 `sratom/0.6.22`
2. meson 直驱交叉构建：`--default-library` 表达库形态（上游 meson_options.txt 无 shared 选项，G2 实证）；pkg-config 两步法（落盘 flags 文件再读回，嵌套 $() 子 shell 在沙箱不稳）
3. 无平台宏（PF5/PF6 合规）；编译器经 tools.build:compiler_executables conf（R33）；源 URL 为 drobilla 官方发布站（PF7）
4. conan-verify 报告中 G0 "构建系统 unknown" / G4 "无法找到程序包 ID" 为门禁工具对 meson 直驱形态识别不全的告警，非阻断——G2 conan create 成功即实质验证（notes.md 末节）
