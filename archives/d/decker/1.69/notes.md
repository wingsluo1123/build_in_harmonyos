# decker 1.69 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-07-20
- 编译器: clang/clang++
- 状态: failed

## 编译步骤

decker 是 Makefile 风格的 C 项目，上游用 `cc ./c/lilt.c -o ./c/build/lilt` 与 `cc ./c/decker.c -o ./c/build/decker` 直接编译两个二进制。conanfile.py `build()` 先 `./scripts/resources.sh` 生成 `resources.h`，再编译 lilt（始终构建），可选编译 decker（`with_sdl=True` 时通过 pkg-config 获取 SDL2/SDL2_image flags）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | c/build/ 目录缺失导致编译输出失败 | git 不跟踪空目录，源码包无 c/build/ | conanfile.py build() 中 `os.makedirs(.../c/build, exist_ok=True)` |
| 2 | with_sdl=True 时 SDL2 flags 静默丢失 | `os.popen("pkg-config ... 2>/dev/null")` 吞掉错误且未关闭管道 | 改用 `with os.popen(...)` 关闭管道；flags 为空时 `raise ConanException` 明确报错 |
| 3 | manifest.yaml status: built 与 .build-closed / notes.md 的 failed 矛盾 | R3/R34 状态真实性违规 | status 统一为 failed |
| 4 | test_package/test.c 仅打印硬编码字符串，未执行 lilt | R34 空壳测试（Critical） | test.c 改为通过 `system()` 执行 `lilt --version` 与 `lilt -e "print 1"`，断言两者均返回 0 |
| 5 | .build-closed 构建标记被提交到 PR | 类似 R19 禁止的 .build-context-* | 从 PR 删除并加入 .gitignore |
| 6 | conandata.yml 含 6 个镜像/代理 URL | 过多镜像违反 URL 规范 | 精简为仅官方 GitHub URL |
| 7 | manifest.yaml sha256 为空 | 源码校验和未填写 | 填入 conandata.yml 中的真实 sha256 |
| 8 | manifest.yaml build.system: autotools 与 build_system: makefile 矛盾 | conanfile.py 用手写 self.run(cc ...) 编译，非 autotools 流程 | build.system 改为 makefile |

## 源码修改

无补丁。conanfile.py 在 build() 中补 `os.makedirs(c/build)`、改用 `with os.popen(...)` 并在 SDL2 flags 缺失时 `raise ConanException`。

## 依赖版本

- with_sdl=False（默认）：无运行时依赖
- with_sdl=True 时需 sdl2/2.30.10、sdl2_image/2.8.0

## 验证结果

```bash
# 构建状态以 .build-closed 与本 notes.md 为准
# 最终状态: failed
```

## 注意事项

- decker 是 application 类型（`cpp_info.libdirs = []`），CMake 测试不可 `target_link_libraries(decker::decker)`；test.c 改用 `system("lilt ...")` 直接执行已安装二进制。
- `.build-closed` 等 CI 构建标记已在 .gitignore 中忽略，不应进入版本控制。

---

**编译结束**: 2026-07-20 10:10
**最终状态**: failed
