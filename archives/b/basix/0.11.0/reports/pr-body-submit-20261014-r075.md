## PR 信息

- **三方库名称**：basix
- **上游版本**：0.11.0（真实适配版本0.11.0）
- **上游仓库地址**：https://github.com/FEniCS/basix
- **适配路径**：路径 A（基础适配） / 路径 B（贡献创新） / 路径 C（高难度挑战候选）
- **使用知识库**：E15119-draft-2301，参考E316与E546，新增同SONAME科学运行库的输入选择及安装后跨语言验收边界。

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 10471 | 原pytest数学套件的唯一参数化节点；不是断言或函数内循环累计 |
| 集成测试 | 0 | 原C++示例消费另述，不重复计入pytest分母 |
| 其他测试 | 0 | 无其他独立上游测试入口计入此分母 |
| **合计** | **10471** | 完整原入口与原注册ID均保留 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|---------------:|------------|------|
| 单元测试 | 10471 | 不变 | 10121 PASS、327 SKIP、23 XFAIL、零意外失败/错误 |
| 集成测试 | 0 | 不变 | 消费者单独计数，不替代原数学验证 |
| 鸿蒙特有测试 | 1 | 新增 | 实际签名程序中计算所得状态的私有POSIX归属、读写与清理 |
| **合计** | **10472** | **+1** | 原350项支持域边界不是通过；新增消费者另计4项 |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [ ] **否**，未修改上游任何测试用例
- [x] **是**，存在对上游测试用例的修改（请在下方逐条说明）

1. `test/test_continuity.py`：原宽RuntimeError捕获掩盖了缺少必需variant
   的输入错误。按同版本原`test/utils.py`设置RT/N1E的legendre及BDM/N2E
   的legendre+DPC参数；原函数、装饰器、132项分母和数学断言保留。
2. `test/test_wcoeffs.py`：移除对四项真实慢测试的时间性skip，保留原
   正交性数学断言；四项在本次每个完整正式create中均真正通过。

其余原数学测试与断言不改。10个源码补丁均由官方refresh-patch --auto
生成，176物化源码字节已核对；不改生成文件、不放宽数学误差、不注入stub。

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

消费者`test_package/test.cpp`调用真实float/double有限元API，2/2；
安装后的Python消费者使用实际包的基函数tabulate和真实NumPy线性运算，
2/2。它们不能替代原10,471项，也不算作鸿蒙特有测试。

`harmony_tests/private_state.py`仅在真实HarmonyOS目标上调用已签名的
消费者专属入口：核对实际uname、由Basix计算所得状态的私有可写目录、
真实进程UID/文件归属、读回一致性、unlink及close结果，1/1通过；不改
系统账户或权限，不把HMDFS投影归属当实际进程UID，也不使用假返回值。

---

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：10121/10471（已确认上游支持域；不宣称100%）
- 新增测试用例通过率：5/5（100%）

每次独立create均10121 PASS、327 SKIP、23 XFAIL、0意外失败/错误；10471原ID逐项一致，不将两次运行相加或称100%。C++2/2、实际安装包Python2/2；鸿蒙专项1/1。

真实事务 `basix-0.11.0-official-20261014-consumertmp132r009` 完成规范ConanVerifier与官方Finish step35；15回执/30WAL、唯一launch、own0/release/postrelease已独立核验。原350项限制均匹配同版本源码支持域，四项原慢数学测试真正执行。350 项边界均来自同版本上游源码：327 项为 continuity 可构造元素组合不足或元素不支持张量积分解时的原生 skip，23 项为上游明确声明尚未实现或不稳定的数学空间/导数自由度情形。已发布的必需依赖均已实际使用；本次 0 个非预期失败、0 个错误。原始 10471 项分母及每项 SKIP/XFAIL 仍完整保留，350 项不计为通过。

- 原JUnit SHA-256：
- 00c109e2ffa42cbba89b20f2f80bcce0647bbead7b99f823ea76da8fadacb543
- 3f6f96fbedbbdfabcfb6eb3aca9d93fb8e8ad195423fb92e04015cdc294e5ba5
- 正式日志 SHA-256：3a37e71cd7ecffe1429a573ae1ac6f22860c6d7f5e510e2d16e41dc44d47c4c1
- 上游支持域证据：archives/b/basix/0.11.0/reports/upstream-supported-domain.json；SHA-256：7d2c7e43990d26d731de4c311e12447d939299602194b3854758ebe1c0aa8967

真实发布依赖为OpenBLAS0.3.34、nanobind2.13.0、robin-map1.4.1；固定23个原测试wheel并保留官方元数据。Conan BLAS与NumPy伴随库同SONAME不同字节，选定前者、排除后者，不覆盖原输入或共享缓存。新HEAD的完整平台CI、Review与提审另行验收，制品尚未发布。

---

## 补充说明

- 关联 Issue：#3958
- 队伍名称：天天开心
- 申请人显示标识：2301_80739235
- 源分支：2301_80739235:feat/basix-0.11.0
- 目标分支：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- 其他说明：任务15119是FEniCS的必要依赖，按真实0.11生态使用，不混用0.10。
  高难度候选申请已公开；官方高难认定以委员会为准。平台CI、最新正式评审
  和提审仍独立验收。只有官方正式发布后才用于下游R36，不手工上传。


保留当前平台request118327/build105153的真实失败：HNP Python在原stubgen中拒绝加载已核验签名的扩展。新配方仅在实例私有根编译并自签一个真正执行PyConfig/Py_RunMain的CPython启动器，运行原stubgen和原完整pytest，不用C测试替换Python绑定。通过所选真实解释器的dladdr定位实际加载libpython，验证启动器的实际版本、标准库prefix和运行库SHA-256，不把sysconfig名称、相同大小或inode当成运行库证明。CMake开发目标使用实际运行库的私有.so副本，保留真实SONAME和提供者，避免版本化.so.1.0被FindPython分类为静态库而追加不适用的私有链接项；不改系统工具、共享缓存或安全权限。旧r005/r006身份检查失败和r007链接缺intl均独立保留、release/postrelease/own0，不重放已launch事务。新正式事务 `basix-0.11.0-official-20261014-pythonlink132r008` 两次独立create各原10471项：10121 PASS、327原SKIP、23原XFAIL、零普通失败/错误；350项源码支持域限制逐项匹配，未累加重复create或将限制算通过。C++2、安装后真实Python2、鸿蒙1，以及15回执30WAL、唯一launch、own0/release/postrelease均独立核验。输入tree `f433180e3476e54bf0dc98e610578b2f371f4900`，正式日志SHA-256 `67dc0e20878ced81e9f3ac78c0534381dd6a256000c9043db57841c1d20ecba2`。这证明该原生事务的真实构建和验证；HNP Worker拒绝的完整系统策略根因仍未确认，新HEAD平台CI与Review另行验收，尚未提审或发布制品。


保留平台request118581/build105407真实终态：私有签名CPython启动器已在HNP Worker完成原stubgen和原数学10121 PASS、327 SKIP、23 XFAIL，C++消费者2/2通过，最后鸿蒙私有文件专项返回RC6。消费者继承的服务投影TMPDIR同时发生make FIFO权限错误；旧RC6未记录具体子检查，不能断言某一系统调用已被证明。新test_package在实际UID所有、规范无链接的POSIX缓存根创建独立0700临时目录，仅对消费者构建和原测试进程绑定TMPDIR；原C++文件归属/读写/unlink/close判断和原Python观察器全部保留，不换UID、预制数据或跳过失败。生产私有CPython启动器与真实运行库绑定保持；新正式事务 `basix-0.11.0-official-20261014-consumertmp132r009` 两次独立create各原10471项：10121 PASS、327原SKIP、23原XFAIL、零普通失败/错误；350项源码支持域限制逐项匹配，不累加重复create。C++2、实际安装Python2、鸿蒙1以及15回执30WAL、unique1/own0/release/postrelease均独立核验。输入tree `d37269fde3fe92cf4bb8b57a97cccef3b6c2fca5`，正式日志SHA-256 `3a37e71cd7ecffe1429a573ae1ac6f22860c6d7f5e510e2d16e41dc44d47c4c1`。本次证明该原生事务完整验证；新HEAD平台CI与Review仍须单独验收，尚未提审或发布。
