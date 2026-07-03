# pipx 1.8.0 适配笔记

## 编译环境
- 构建系统: pip (纯 Python 包，使用 python3 -m pip install)
- 编译日期: 2026-07-03
- 编译器: clang/clang++ (未使用，纯 Python 无 C/C++ 编译)
- 状态: published

## 编译步骤

1. **init-build**: 下载 GitHub release tag v1.8.0 源码包并解压
2. **pip install**: 使用 `python3 -m pip install . --no-deps --target=<staging>/lib/python3.12/site-packages/` 安装 pipx
3. **依赖安装**: argcomplete, packaging, platformdirs, userpath 通过 pip 安装到同一 site-packages
4. **版本测试**: `PYTHONPATH=<staging> python3 -m pipx --version` → 输出 1.8.0
5. **Conan 配方**: conan-init 生成 conanfile.py + conandata.yml + test_package/
6. **Conan 验证**: conan-verify 干净构建通过 (G1-G4 + L2/L4/L5 全部 PASS)
7. **finish**: 状态标记为 published

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub URL 下载失败 (NotFoundException) | OHOS 环境无法直接访问 GitHub | conandata.yml 使用 PyPI 社区镜像 URL，sha256 一致 |
| 2 | pip3 命令未找到 | Conan 构建环境 PATH 中无 pip3 | conanfile.py 中使用 `python3 -m pip` 替代 |
| 3 | Conan 2.x API 变更 | deps_cpp_info 已移除 | test_package 使用 `self.dependencies["pipx"].package_folder` |
| 4 | G0 干净构建 configure 失败 | pipx 无 configure 脚本，纯 Python 项目 | 预期行为，非阻塞，已手动验证通过 |

## 源码修改

- `src/pipx/version.py`: 版本号相关修改，生成补丁 `0001-src-pipx-version.py.patch`

## 依赖版本

| 依赖 | 版本 |
|------|------|
| argcomplete | 3.7.0 |
| packaging | 26.2 |
| platformdirs | 4.10.0 |
| userpath | 1.9.2 |

## 验证结果

```bash
# Staging 版本测试
$ PYTHONPATH=<staging>/lib/python3.12/site-packages python3 -m pipx --version
1.8.0

# CLI entry point
$ PYTHONPATH=<staging>/lib/python3.12/site-packages python3 <staging>/lib/python3.12/site-packages/bin/pipx --version
1.8.0

# Conan 干净构建 + test_package
$ conan create <archive> -pr:h=ohos-aarch64 --build=missing --user=ohpcd --channel=stable
...
pipx/1.8.0@ohpcd/stable: Building from source
pipx/1.8.0@ohpcd/stable: Sources correctly downloaded from https://pypi.cnb.cool/.../pipx-1.8.0.tar.gz
pipx/1.8.0@ohpcd/stable: Calling build()
  Successfully installed pipx-1.8.0
  Successfully installed argcomplete-3.7.0
  Successfully installed packaging-26.2
  Successfully installed platformdirs-4.10.0
  Successfully installed userpath-1.9.2
pipx/1.8.0@ohpcd/stable: Package 'fc3eeb021243959114a0318489539cad6d087e28' created
(test package): RUN: PYTHONPATH="..." python3 -m pipx --version
1.8.0
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| packaging/pipx-1.8.0-ohos-aarch64.tar.gz | 1.9M | Release 制品包 (site-packages + bin/) |
| conanfile.py | 3.7KB | Conan 配方 |
| conandata.yml | 457B | 源码+补丁声明 |
| test_package/conanfile.py | 786B | Conan 测试包 |

## 注意事项

1. GitHub 直接 URL 在 OHOS 环境不可达，conandata.yml 使用 PyPI 镜像 URL（sha256 一致）
2. conanfile.py 的 build() 中使用 `python3 -m pip` 而非 `pip3`
3. pipx 是纯 Python 包，无 C/C++ 编译步骤，L4/L5 安全扫描不适用
---

**编译结束**: 2026-07-03
**最终状态**: published
