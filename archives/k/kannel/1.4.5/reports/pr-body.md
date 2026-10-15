## PR 信息

- **三方库名称**：kannel
- **上游版本**：1.4.5
- **上游仓库地址**：https://www.kannel.org/
- **适配路径**：路径 A（基础适配） + 路径 B（贡献创新）
- **使用知识库**：E7739-draft-2501（本PR新增配对草稿）

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 5 | 完整 checks/*.c 注册可执行组，见 MANIFEST |
| 集成测试 | 9 | 完整 checks/*.sh 注册检查组，含编译/头文件、WAP、SMS、HTTP/HTTPS、PPG、SMPP |
| 其他测试 | 0 | 原注册检查均已计入上述两行，未重复计数 |
| **合计** | **14** | Makefile checks 完整枚举：5 C + 9 shell，无跳过 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|---------------:|------------|------|
| 单元测试 | 5 | 不变 | 保留全部原输入、配对和比较；字节 oracle 修改明确披露 |
| 集成测试 | 15 | +6 | 原9组 + 5安装API组 + 1安装gw-config编译/链接/运行组 |
| 鸿蒙特有测试 | 0 | 不变 | ENOTSUP与协作wake/join包含在消费者中，不重复计数 |
| **合计** | **20** | **+6** | 原上游14组 + 独立消费者6组 |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [ ] **否**，未修改上游任何测试用例
- [x] **是**，存在对上游测试用例的修改（请在下方逐条说明）

1. `checks/check_octstr.c`：OHOS原生strcasecmp与unsigned-byte/ctype算法对高位字节不一致；用独立显式字节顺序作为期望，保留六个原字符串、36对case比较及原strcmp检查，不改生产Octstr算法。
2. `checks/check_http.sh`：只把只读/tmp中的client PEM改为任务build路径，原请求/退出检查不变。
3. `gw/cert.pem`/`gw/key.pem`测试夹具：原弱密钥被OpenSSL3拒绝；每次由已声明OpenSSL生成RSA2048/SHA256匹配测试证书，未降低TLS安全级别、未禁用HTTPS，实际测试私钥不提交/不安装。
4. `upstream_support/strict_checks.py`：完整枚举5 C + 9 shell，严格传播原退出码/错误，超时与残留进程只在本测试session/start/UID/boot/CONAN_HOME匹配后清理。

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

上游已有完整注册检查。新增 test_package/test.c 的5组安装API消费者和 test_package/conanfile.py 的1组安装gw-config真实编译/链接/运行验证，独立计数，不替代上游。

---

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：14/14（100%）
- 新增测试用例通过率：6/6（100%）

独立原生事务 kannel-w3-r19-20261013：14/14、6/6与12阶段W3_PASS；日志SHA256 78dd78a9e05af4eddabdee83a3170b585f68075e01a4ed180169296c617a52be。同产品输入的official finish r2中G1/G2及本地CI子步骤通过，finish整体RC1是旧step5b/step8标记限制；r2自身最终W3校验因旧5组口径失败，不声明其W3_PASS。r19重新完整执行，不拼接旧测试。官方.ci-result.json只读保留，未伪造或改框架。比赛worker CI与平台Review尚未完成。

---

## 补充说明

- 关联 Issue：#3964
- 队伍名称：诶，云朵
- 申请人显示标识：2501_91199785
- 源分支：2501_91199785:feat/kannel-1.4.5
- 目标分支：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- 其他说明：基础库任务 #7739；路径 A+B，四项HD条件当前均不匹配。字节 API 的 unsigned-byte/ctype 契约与 native strcasecmp 高位字节排序可能不一致；先核对接口、locale 和独立 libc 证据，再用独立显式 byte oracle 保留所有原始输入/比较，而不是删案例或改生产算法追随不一致 oracle。包含不能泛化为全部非法 UTF-8 等价的反例及已安装二进制字节验证。 静态支持库与网关按上游构建；未验证外部运营商设备互操作，未发布制品。


### 2026-10-14 当前 CI 修复

Autoconf creates config.status scratch directories in two branches with owner-only masks. On HMDFS, changing file modes later or repairing PR transport cannot establish creation-time access. Replace both creation branches with exclusive mkdir under the recipe-private TMPDIR, use umask 022 at creation, restore configure timestamps, and prefix TMPDIR after Conan environment activation. Preserve cleanup and every original test.

当前真机事务 `kannel-ci-repair-w3-20261013-r101`：12阶段和释放 PASS，官方本地CI子步骤 exit0；原始CI日志 SHA256 `e5cde636a55bc6f30b6927231665697a4cfd9d02124d68942d8750ef91d164a9`。上游 14 项和消费者 6 程序的声明与断言未减少。配套草稿补充上述可复用边界。完整finish旧归档/格式/就绪标记失败保留，不宣称整个finish RC0；比赛worker CI、最新AI检视、审核和发布仍需针对修复提交确认。


### 2026-10-14 当前 CI 修复

Consumer compilation and consumer execution require different environment scopes. Use conanbuild for invoking the configured compiler and gw-config flags; activate conanrun only for the installed consumer execution. Mixing host runtime library directories into the SDK compiler process can select an incompatible libxml2 provider for lld.

当前真机事务 `kannel-ci-repair-w3-20261013-r202`：12阶段和释放 PASS，官方本地CI子步骤 exit0；原始CI日志 SHA256 `65044d7f0ab4a2472c2a3cad980ae5b2ee76bfe18bfc4a0814bb80542f08481e`。上游 14 项和消费者 6 程序的声明与断言未减少。配套草稿补充上述可复用边界。完整finish旧归档/格式/就绪标记失败保留，不宣称整个finish RC0；比赛worker CI、最新AI检视、审核和发布仍需针对修复提交确认。
