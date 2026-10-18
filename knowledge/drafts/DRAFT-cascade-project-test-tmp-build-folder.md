# Conan 配方的项目级测试临时目录应限定到 build_folder

> 路径 B 知识草稿；与同 stem 的 `.kv` 配对，待审核后再决定是否提升。
> 来源：cascade-compiler g20200105.1，PR !15713。

## 触发条件

上游测试或适配补丁通过项目专用环境变量（例如 `CASCADE_TMP_DIR`）选择运行期
scratch/cache 目录。HarmonyOS 的 `/tmp` 不可写，而 Conan 为主包与 `test_package`
分别提供独立的 `self.build_folder`。

## 根因分析

将项目专用目录写成某台设备上的固定绝对路径，会把测试状态绑定到旧任务的目录，
而不是当前 Conan build。`os.makedirs(..., exist_ok=True)` 还会复用该路径已有的
内容，造成并行任务之间的碰撞或权限失败。标准 `TMPDIR` 不能代替项目变量：上游
补丁读取的是 `CASCADE_TMP_DIR`。

修复方式是从当前 recipe 的 `self.build_folder` 派生目录，并在 test package 中
再次使用它自己的 `self.build_folder`。这样每个 Conan 构建有自己的 scratch 根目录，
且不依赖设备账号、工作区名称或共享临时目录。

本例还说明要区分临时目录问题与单个测试的调用路径：上游
`simple.hello_3` 使用 `regression/minimal` 软件模拟目标；它不连接 stdin，不选择
JIT 目标，也不调用硬件模拟器使用的 `System::tmp_root()`。因此该目录隔离修复适用于
整套硬件软件模拟回归，但不能单独证明它造成了 `simple.hello_3` 的超时。

## 解决方案

```python
cascade_tmp_dir = os.path.join(self.build_folder, "_cascade_tmp")
os.makedirs(cascade_tmp_dir, exist_ok=True)
self.run('CASCADE_TMP_DIR="{}" ctest ...'.format(cascade_tmp_dir), env="conanbuild")
```

`test_package` 也在自身 `self.build_folder` 下创建 `_cascade_tmp`，再把该路径传给
消费者可执行文件。并行上限应独立设置；本例直接调用
`cmake --build <build_folder> --parallel 2`，避免混淆构建并发与运行期 scratch 路径。

## 查重反证

- `coinor-vol-1.5.4-tmpdir-writable-probe-fallback` 讨论标准 `TMPDIR` 候选目录的
  可写性探测；本草稿记录的是项目自定义变量必须绑定到每个 Conan build。
- `DRAFT-lazperf-3.4.0-tests-hardcoded-var-tmp-readonly-rootfs` 讨论上游测试把
  文件硬编码到 `/var/tmp`；本例上游已支持环境变量，缺陷在 recipe 固定了设备路径。
- `DRAFT-shared-fs-inode-exhaustion` 约束清理其他活动任务的文件；本草稿从 recipe
  侧隔离新建的测试 scratch，不涉及清理或访问其他任务目录。

## 验证

HarmonyOS aarch64 实测记录保存在 `archives/c/cascade-compiler/g20200105.1/reports/`。
完整上游 GoogleTest 运行了 294 个用例、16 个 suite，294 通过、0 失败、0 跳过；
CTest 的 regression 入口为 1/1 通过。`simple.hello_3` 单测在同一设备重复运行 500
次，500 次通过。Conan create 退出码为 0，随后 `test_cascade` 消费者可执行文件运行
成功。

## 适用边界

适用于 recipe 可控制项目专用测试临时目录的场景。若上游二进制硬编码 `/tmp`、
`/var/tmp` 等路径，设置项目变量不会改变其行为，需要针对上游路径做单独适配。

## 元信息

- Draft ID：`DRAFT-cascade-project-test-tmp-build-folder`
- Contributor：`iKalous_OscarP`
- PR：!15713
- 更新时间：2026-10-16
- 状态：`draft: true`
