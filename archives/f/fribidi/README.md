# FriBidi

## 简介
GNU FriBidi 是 Unicode 双向算法 (Bidirectional Algorithm) 的实现库，用于正确处理阿拉伯语、希伯来语等从右到左（RTL）文本与从左到右（LTR）文本的混合排版。

## OHOS 适配
- **构建系统**: autotools (configure + make)
- **编译器**: clang/clang++
- **补丁**: config.guess/config.sub OHOS 平台检测
- **运行时修复**: shebang (E165), umask (E110) 在 conanfile.py build() 中处理

## 依赖
- 无额外库依赖

## 功能验证
```bash
fribidi --version
fribidi --help
```

## 参考
- GitHub: https://github.com/fribidi/fribidi
