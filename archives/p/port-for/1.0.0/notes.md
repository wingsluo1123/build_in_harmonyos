# port-for 1.0.0 适配笔记

账号gcw_tlRDjnsx，task9665，路线新适配A+B，分支feat/port-for-1.0.0。准确sdist21681B/SHA256404d161b1b2c82e2f6b31d8646396b4847d02bf5ee10068c92b7263657a14582。实际Python源码；平台历史cpp/url=null未修改。MIT，上游地址https://github.com/fizyk/port-for。

生产只将api.py中to_ranges(list(ports))改为to_ranges(sorted(ports))；utils的value-index分组需要数值有序输入，set迭代可折返使连续区间碎裂再被最小长度门槛过滤。原端口范围/border/socket语义保留。补丁追加一条非模拟的set区间回归，原测试不删、不改、不增跳过。

## 原测试清点与实际本机结果

准确sdist的pyproject.toml指定testpaths=tests。完整pytest实际收集22项：tests/test_cases.py15项、test_select_port.py2项、test_store.py5项。test_random_port内部100次循环计为一个pytest注册项。

| 阶段 | 注册 | 通过 | 失败 | 跳过 | 说明 |
|---|---:|---:|---:|---:|---|
| 原版本机完整上游 | 22 | 21 | 0 | 1 | 原Windows低端口绑定skipif |
| 新回归/未修API | 1 | 0 | 1 | 0 | [] != [(1003,1036)] |
| 修后本机完整（含新增1项） | 23 | 22 | 0 | 1 | 同一上游skipif |
| 本机wheel真实消费者 | 1程序 | 1程序 | 0 | 0 | 11功能检查+2身份断言，非13程序 |
| 目标修后完整套件（保留22+新增1） | 23 | 23 | 0 | 0 | 0.51s，原断言/skip条件不改 |
| 目标Conan真实消费者 | 1程序 | 1程序 | 0 | 0 | 11功能检查+2身份断言，实际包模块 |

本机为Windows10/Python3.11.0rc2/pytest9.0.2。原完整上游实际RC0；记录器在打印日志时GBK编码失败RC1，保留控制错误，仅修控制台输出并自然继续首次红/绿回归，没有重放原套件。完整命令、原stdout/stderr及固定摘要由本任务唯一ENTRY给出。

## 配方与必要目标验证

配方保留上游setuptools构建wheel，生产Python3.12.9；测试requires精确pytest9.1.1/iniconfig2.3.0/packaging26.3/pluggy1.6.0/pygments2.20.0.1 RREV，并显式加入它们的交付site-packages路径。六个固定Conan包目标下载均RC0、真实Python3.12.9/pytest9.1.1/Pygments2.20.0导入RC0；修正test_requires不支持的libs参数后目标图解析RC0，原遗漏依赖与图失败保留。真实目标原版观察已完成、新增红测试1FAIL，首次官方conan-verify G2构建RC1：build-tools工具文件存在，但PYTHONPATH因初始普通define成为空格分隔字符串，导致setuptools导入失败。仅改为define_path，env脚本及self.run调用保持；目标生成的PYTHONPATH已实际以冒号分隔，官方conan-verify自然RC0、完整pytest23PASS/0FAIL/0SKIP（0.51s）、Conan test_package消费者RC0（1程序/11功能检查+2身份断言）。pygments固定公开供应完整ref/PID/PREV在ENTRY给出。另Conan Python的sqlite3导入缺符号、额外distribution metadata探测失败分别保留，不称port-for测试失败。setuptools84.0.0与wheel0.45.1官方纯Pythonwheel固定URL/SHA；仅解入build_folder私有build-tools，不装系统或修改HOME。build()必须执行完整python -m pytest tests，再构建wheel；test_package从真实Conan包验证端口与持久化流程，显式can_run失败不能冒称通过。

源码离线输入只接受PORT_FOR_SOURCE_ARCHIVE且重验官方SHA；构建工具离线输入PORT_FOR_BUILD_TOOL_INPUT逐文件重验SHA。CI同源file://预下载只在运行时读取，提交conandata全部为官方HTTPS，不含本机路径。运行时库路径只来自Conan包。原CLI默认/etc/port-for.conf，消费者只用私有临时文件，不改上游默认或系统配置。commands.json binary=false，尚未发布。

目标为OHOS6/armv8/Python3.12.9，原set观察与未修API新增红测试1FAIL已取得，修后保留上游22项再加1回归共23项全部通过；另1真实Conan消费者程序通过，合计声明24项，功能检查与身份断言分列。实际包ref为port-for/1.0.0@ohpcd/stable#bbbbce9164b080026a38a3bdf3367d2c:da39a3ee5e6b4b0d3255bfef95601890afd80709#8259ab313771901978a9d802a661add1，消费者读取该包p/lib/python/port_for/__init__.py。官方G4未识别包ID、L2/L4/L5无cache路径跳过等边界保留，不称这些审计已执行。首次正式W3在私有图谱输入缺失的G0前置FAIL，原件保留；准确548官方blob补供后，正式W3 setup/build_and_test自然RC0，G0/KC/JC（完整13文件）/L0/L1/L4/L5实际PASS，第二次完整pytest23PASS（0.55s）及真实Conan消费者通过。L2裸CLI version/help失败后skip，不称smoke通过；整次finish仍RC1，旧归档及私有全图谱收口问题分列。manifest记录built（实际Conan构建/交付成功，未远端发布）；正式W3证据有效，旧finish RC1与当前PR门分列；不新增运行器、轮询、桥或共享写窗。

知识草稿E9665-draft-9665由官方graph add --draft入口生成、作者填正文，实际解析/匹配验证见ENTRY。B02仅三篇固定近邻限定增量；不宣称全库原创。申请Issue/PR及其当前CI、真实AtomCode、任务面板关联和有效提审按实际当前head单独核，不以本地测试替代官方状态。

### 对话 #1 用户目标与本轮实测

用户目标为完成GCW port-for1.0.0/task9665的真实路径B最低完整交付并取得当前PR有效提审回读。原作者已完成真实缺陷的一行排序修正、保留原22项并新增1回归；唯一H1取得原API红测试1FAIL、修后23PASS与真实包消费者成功，固定官方输入补供后的W3通过。CLI裸smoke skip与finish归档失败按下文边界保留，不冒称当前CI/AtomCode/提审完成。

## 发现与知识

- ✅ 已形成可消费的无序集合连续分组/长度过滤草稿，knowledge_ref: drafts/E9665-draft-9665.kv；原失败精细消费命中6，修后和3反例均0，仅该消费范围，不称正式索引纳入。

## Conan运行环境与旧收口边界

标准生产VirtualRunEnv已在目标实测：固定ref本地conan install --build=never --no-remote -g VirtualRunEnv返回0，全部Cache/Skip，无构建或下载；激活真实conanrun.sh后CLI version/help均RC0，模块来自p/lib/python/port_for/__init__.py，解释器来自生产Python包。裸调用的两条原命令均RC1/ModuleNotFoundError，原L2 skip保留，不能倒写为旧smoke PASS；bash shell-init的getcwd权限警告保留。准确542篇基线MD补供后首次官方graph validate RC0，170原有警告和旧W5四个多行字段扫描误报单列，未改他人KV/index。

整体finish RC1原记录保留。按R19/R20及本项目限定裁决，本项使用实际官方Conan交付、真实安装消费者及标准生产运行环境证据；不补残留PackageBuilder tar/debug/空staging标记，不据此声称官方豁免。真实CI禁止这类运行标记/打包产物入PR，自动生成SUMMARY也不属于本软件提交。软件源/配方/测试已过证据复用，新增命名报告只据原件陈述事实。状态：built（Conan目标包已构建，未远端发布）。
