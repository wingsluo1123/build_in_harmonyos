# bazel-diff 18.0.0 适配笔记

## 构建信息
- 构建系统: 预编译 JAR (Bazel 8.5.1 构建于 x86 机器)
- 语言: Kotlin (JVM)
- 产出物: bazel-diff.jar (自包含 fat JAR, 14MB)
- Main class: com.bazel_diff.Main
- 运行时要求: JDK 21+

## 构建方式
Bazel 无法在 OHOS aarch64 上运行 (HMDFS/SELinux 限制)，kotlinc 也不在 CI worker 上。
使用预编译的 deploy JAR (JVM 字节码平台无关)，通过 export_sources() 导入 conanfile.py。

原始构建命令 (在有 Bazel 的机器上):
```bash
bazel build //cli:bazel-diff_deploy.jar -c opt
```

## OHOS 适配说明
- JVM 字节码平台无关，JAR 可直接在 OHOS 上运行（需 JDK 21+）
- Bazel 工具链在 OHOS aarch64 上因 HMDFS/SELinux 限制无法直接运行
- 使用预编译 deploy JAR 通过 Conan export_sources() 打包，CI 无需 kotlinc/Bazel
- 运行时需安装 JDK（bishengjdk 17 或 JDK 21+）

## 依赖
- com.google.code.gson:gson:2.9.0
- com.google.guava:guava:31.1-jre
- info.picocli:picocli:4.6.3
- io.insert-koin:koin-core-jvm:4.0.0
- org.apache.commons:commons-pool2:2.11.1
- org.jetbrains.kotlinx:kotlinx-coroutines-core-jvm:1.5.2
- com.google.protobuf:protobuf-java:4.35.1
