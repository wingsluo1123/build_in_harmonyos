# DRAFT-smartlist-3.15-noshell-direct-exec-retry-fix-oom
> 低内存真机报/bin/sh Out of memory时免sh直调降fork治构建OOM
## 问题特征（真实日志片段/标记）
- 真机compile阶段报/bin/sh: Out of memory，上游测试发现0执行0
- 配方原三次self.run为shell字符串，经shell转调，每次多fork一次/bin/sh
- 低内存真机jobs为1，小构建仍因fork失败报OOM，非编译器内存瓶颈
## 根因
- 配方build()三次self.run(shell字符串)每次多fork一次/bin/sh，内存紧张时fork失败报OOM；smartlist仅编译hsort.c/gethome.c两个小文件，编译器内存非瓶颈
- shell字符串转调和外部产物检查放大了fork次数，资源不足时直接触发Out of memory或can't fork类失败
## 修复方案（rec）（编号步骤，含具体文件与命令）
1. 在archives/s/smartlist/3.15/conanfile.py新增_run_noshell，以argv数组直调subprocess且不经shell，对Out of memory/can't fork/EAGAIN/ENOMEM做1/2/4s有界重试，其余错误立即抛
2. 将三次编译/归档调用由shell字符串改为argv直调，产物用os.path.isfile/getsize进程内校验替代外部shell检查
3. 对test_package/conanfile.py同样改造test_hsort编译为argv直调并做产物校验，保持测试口径与产物语义不变
4. 用py_compile校验配方语法，真机复检确认compile阶段无/bin/sh: Out of memory且产物校验通过
## 禁止策略
- 禁止保留shell字符串转调和外部产物检查，禁止对真实编译错误做重试掩盖
- 禁止在仍报OOM/fork失败时伪造通过标记；仅fork资源特征允许有界重试，否则门禁不通过并退回修复循环
## 与相近条目的边界（查重）
- 可抽象出通用内核：低内存真机小构建报/bin/sh Out of memory时，去掉shell字符串转调改argv直调、产物检查进程内化、仅对fork资源特征有界重试
- 强增量：查重无OOM/fork/noshell条目，最接近的E3211只解决compiler path missing回退，与本任务fork失败根因和解法正交
## 适用判断
- 适用于真机报/bin/sh: Out of memory或can't fork且构建仅需少量编译器调用时
- 不适用于真实编译错误、大型并行构建内存瓶颈或编译器缺失路径问题；真实编译错误须立即失败，不改变测试口径与产物语义
