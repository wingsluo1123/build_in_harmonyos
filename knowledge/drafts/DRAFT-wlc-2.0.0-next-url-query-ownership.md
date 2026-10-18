# next 完整 URL 已拥有 query 时，不再重放首次 params

适用对象是跟随服务端完整 `next` URL 的分页 HTTP 客户端。wlc 2.0.0 是本次固定实例；这是通用逻辑缺陷，不限定 OHOS。

## 症状、触发与根因

在 `Weblate.list_factory("translations/", Translation, params={"page": 1, "q": "hello"})` 中，第一页保留用户参数。响应固件提供完整的 `http://127.0.0.1:8000/api/translations/?page=2`。原循环每轮仍传同一 params，requests 2.32.5 的 PreparedRequest.prepare_url 把编码参数追加到已有 query，实际得到 `page=2&page=1&q=hello`。

固定原始源码加新增离线回归的真实失败是：

```text
AssertionError: {'page': ['2', '1'], 'q': ['hello']} != {'page': ['2']}
```

服务端如何解释重复 page 取决于具体协议；本次没有连接真实 Weblate，没有证明死循环或遗漏记录，也不从这个失败推断所有服务端均采用末值。

## 最小方案与边界

```python
while path is not None:
    data = self.get(path, params=params)
    # The server's next URL already contains its query parameters.
    params = None
    # 保留原 results/next 处理及所有 URL/同源验证。
```

清空的是循环局部变量。首请求仍接收原 page 和 q，调用者字典保持不变；第二、第三页只使用 next 中的 page=2/3。没有删除同源检查，也没有修改请求参数编码规则。

仅在 next 是权威完整 URL、已携带后续查询语义时采用此方案。next 仅返回路径、要求每次添加独立过滤/签名参数或使用游标请求体的 API，需按它们的协议分别决定参数归属，不能直接照搬。不要用删 page 参数、覆盖所有 requests query、禁用同源检查或放宽回归断言掩盖问题。

## 可复现验证

固定源为 PyPI wlc 2.0.0 sdist，SHA256 `bd499954d3e27e8bb211d2eb9bb5a91cdd4120ed9d5fb8c273296ff22f97d826`。补丁保留全部 9 个原 test_ 模块、原断言及 fixtures，只新增一个 `tests/test_pagination.py` 方法。测试仍使用原 responses 0.26.0，读取 translations、translations--GET--page=2、translations--GET--page=3 三个未修改固件，不需要账号或 Weblate 实服。

在应用配方补丁后的源码根目录，使用已具备 conandata 固定构建/测试依赖的 Python3.12 执行：

```sh
python3.12 -B -m unittest discover -s tests -t . -v
```

原版在 Windows CPython3.12.14 下动态执行 218/218；原版加新回归 0/1，错误如上；修复后 219/219。177 个静态方法定义不等于 218 个动态执行项，额外方法来自实际 unittest 发现/继承。回归检查首参一次、page2/3唯一、三请求后 next=null、50 个唯一 URL 及输入字典未变。原同源/端口/URL 验证测试仍在原 suite 中。

另一个安装包消费者使用真实 requests 与标准库本机 HTTP 服务，实际从本次构建并安装的 wheel 导入；三次请求、50 个唯一结果、有限终止均 PASS。这是一个消费者程序，三次请求与 50 条数据不分别计为测试。回环消费者用于证明已安装包的行为，测试隔离本身不作为本条的新颖性。

H1-008：OHOS aarch64 / Python3.12.9 / Conan2.29.1，原有218/218和一个安装消费者通过（3次请求、50个唯一结果）；正式 Conan create/verify rc0，官方 W3 工具 rc0。H1-008 新增回归因落在 source root 未被收集，原 HOLD 保留。H1-009：官方 Conan source()/apply_conandata_patches rc0，唯一 tests/test_pagination.py 字节正确，新增单测单独1/1 PASS。两批证据共覆盖218个原用例和1个新增回归，不声称一次合跑219；009未重建Conan包或重跑W3。008的 wlc --version/--help 保留官方非阻塞 L2 SKIP/WARNING。 完整finish未执行，PR官方CI尚待创建PR后取得。

## 近邻差异与来源

官方知识比较固定在 main `e3aaad7dbbf22edf5830f26209e519c82d9111a3`：cloud-utils ec2metadata 的 IMDS mock 条目处理硬编码服务和离线验证；restclient-cpp loopback 条目处理公网服务测试隔离；Issue3781 处理 PF10 全局草稿占用扫描的分页完整性。三者没有描述“完整 next URL 与首请求 params 被同时用于后页请求”的状态所有权。本条不主张全球原创，不修改他人的条目或全局索引。

- [上游源码](https://github.com/WeblateOrg/wlc)
- [固定 PyPI 版本](https://pypi.org/project/wlc/2.0.0/)
- 对应归档：`archives/w/wlc/2.0.0/`，精确源码/依赖 URL 与 SHA 见 conandata.yml；完整真实阶段见 notes.md。
