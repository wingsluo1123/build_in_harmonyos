# ppft

- **上游**：https://github.com/uqfoundation/ppft
- **版本**：1.7.8
- **形态**：纯 Python（noarch）分布式/并行工具（pathos 的 parallel 分叉）
- **运行期依赖**：**无**（PyPI `requires_dist` 为空；`dill>=0.4.1` 仅为可选 extra）

## 归档内容

```
1.7.8/
  conandata.yml            源（官方 sdist + sha256，钉死）
  conanfile.py             配方（source → build(测试期依赖 + 上游测试动态探测) → package）
  manifest.yaml            版本级 manifest（零依赖 / upstream_tests / knowledge_gained）
  notes.md                 适配要点与待办（网络恢复后回填实测数字）
  test_package/            消费者校验（6 项，全部离线，只用可实证断言）
```

## 状态（如实披露）

- **归档已完整、配方与消费者校验已就绪** ✓
- **本地 CI 复验 / 上游测试真实通过率 / 提交推送 / PR+issue：待网络恢复后完成** ✗
  （本轮本机 DNS 故障，取 sdist 与推送均不可进行）
- 上游测试目录以 **动态探测**处理并在探测不到时**响亮失败**（不冒充通过）
