# bazel-diff 18.0.0 适配笔记

## 构建信息
- 构建系统: Bazel 8.5.1
- 语言: Kotlin (JVM)
- 产出物: bazel-diff_deploy.jar (自包含 fat JAR)
- Main class: com.bazel_diff.Main
- 运行时要求: JDK 21+

## 构建方式
```bash
bazel build //cli:bazel-diff_deploy.jar -c opt
```

## OHOS 适配说明
- JVM 字节码平台无关，JAR 可直接在 OHOS 上运行（需 JDK 21+）
- Bazel 工具链在 OHOS aarch64 上因 HMDFS/SELinux 限制无法直接运行
- 需要在有 Bazel 的构建机上交叉编译后部署 JAR
- 已安装 openjdk@21 (Harmonybrew) 和 kotlin 2.4.0 可用于运行

## 依赖
- com.google.code.gson:gson:2.9.0
- com.google.guava:guava:31.1-jre
- info.picocli:picocli:4.6.3
- io.insert-koin:koin-core-jvm:4.0.0
- org.apache.commons:commons-pool2:2.11.1
- org.jetbrains.kotlinx:kotlinx-coroutines-core-jvm:1.5.2
- com.google.protobuf:protobuf-java:4.35.1
