# E431 — 鸿蒙 XPM 代码签名：未签名的打包 ELF 无法 exec/dlopen

## 错误特征

```
ws/11.4.6@ohpcd/stable (test package): RUN: ".../p/bin/ws" --version
/system/bin/sh: .../p/bin/ws: Operation not permitted     # rc=126
ERROR: ... Error in test() method — ConanException: Error 126
# dlopen 未签名 .so 同理报 Permission denied / dlopen failed
```

conan create 全流程（编译、打包）都成功，test_package 里执行包内 CLI 才失败。

## 触发条件

- 构建系统: conan 配方 package()（cmake.install）+ test_package self.run(包内 bin)
- 阶段: installation / testing
- 鸿蒙 PC 真机（XPM 内核策略生效）

## 根因分析

鸿蒙 PC 的 XPM 要求被 exec 的可执行文件与被 dlopen 的共享库带有效代码签名
（ELF 的 .codesign 节）。cmake install 原样复制构建产物，没有签名环节，因此
包内二进制一运行就被内核拒绝。

## 解决方案

### 推荐方案

配方 package() 末尾加 `_sign_binaries()`（本仓 fmt/spdlog 配方已是此模式）：
对 `lib/**/*.so*` 与 `bin/` 下 ELF 逐个：

```python
objcopy = "/data/service/hnp/bin/llvm-objcopy"
signer  = "/data/service/hnp/bin/binary-sign-tool"
self.run(f'{objcopy} --remove-section .codesign "{f}" 2>/dev/null || true')
self.run(f'{signer} sign -inFile "{f}" -outFile "{f}" -selfSign 1')
```

要点：先 remove 再签（幂等）；`.so` 版本符号链接跳过，只签真实 ELF；
整段用 `if self.settings.os != "OHOS": return` 守卫（签名工具只存在于 OHOS）。

### 禁止做法

- ❌ 把已签名二进制 `git add -f` 进归档（制品不入库，JC2 会拦截）
- ❌ 消费者侧安装后再签名（包不可复用）

## 验证

```bash
conan create archives/w/ws/11.4.6 -pr:h ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
# test_package: ws ixwebsocket/11.4.6 linux ssl/OpenSSL OpenSSL 3.5.8 ...
```

## 关联条目

- 相关: E220（Operation not permitted 的 ln 场景）、E298（conanrun 环境）
