# Spark 4.1.2 — 适配笔记

## 软件信息
- 软件名: spark
- 版本: 4.1.2
- 类型: JVM 预编译分发包 (Apache Spark with Hadoop 3)
- License: Apache-2.0
- Homepage: https://spark.apache.org/
- 状态: built

## 构建系统说明
Spark 4.1.2 使用官方预编译包 `spark-4.1.2-bin-hadoop3.tgz`，无 configure/make。Conan 配方负责下载、校验 SHA256/SHA512、解压、复制 `jars/`、`examples/`、`python/`、`R/`、`conf/` 等目录，并生成 OHOS 兼容包装脚本。

## 依赖
- bishengjdk/OpenJDK 17+，本机验证使用 BiSheng JDK 17.0.13。
- Python/R 仅用于 `pyspark` 和 `sparkR`，核心 `spark-submit` + SparkPi smoke test 不依赖它们。

## 关键适配点
1. `java.home` 正常，但 HarmonyOS JVM 默认 `os.name=HarmonyOS`，Spark/Hadoop 部分 Java 平台判断需要 Linux 兼容路径。包装脚本设置 `-Dos.name=Linux`。
2. JVM 在部分场景会报告 `user.home=?`，导致 Ivy 构造 `?/.ivy2.5.2/local` 并报 `basedir must be absolute`。包装脚本设置 `-Duser.home=$HOME`。
3. HarmonyOS UID 可能没有 passwd 记录，`whoami` 返回 `cannot find name for user ID`，Hadoop UGI 会触发 `invalid null input: name` 或 `Invalid UID`。包装脚本设置 `SPARK_USER`、`HADOOP_USER_NAME`、`-Duser.name`。
4. 上游 `load-spark-env.sh` 会被 `spark-class` 通过 `.` source，包装版本必须 source-safe，不能直接 `exec`。

## 验证结果
- `conan create archives/s/spark/4.1.2 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohos --channel=stable` 通过。
- test_package 执行 `spark-submit --version`，确认输出 `version 4.1.2`。
- test_package 执行上游 SparkPi 示例: `spark-submit --class org.apache.spark.examples.SparkPi --master local[1] spark-examples_2.13-4.1.2.jar 2`，输出 `Pi is roughly ...`。
- `graph validate` 通过，存在 12 个仓库既有 warning，非本次 spark 新增。

## 归档文件
- `conanfile.py`: 下载、校验、打包并生成 OHOS 兼容包装脚本。
- `conandata.yml`: 官方 Apache 下载 URL，含真实 SHA256 与官方 SHA512。
- `test_package/`: 消费者视角真实 Spark smoke test。
- `commands.json`: 声明 spark 为命令行工具包。

---

**编译结束**: 2026-07-14 14:08
**最终状态**: built
