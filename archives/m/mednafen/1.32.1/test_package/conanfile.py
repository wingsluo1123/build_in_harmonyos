import json
import os
import re

from conan import ConanFile


class MednafenTestConan(ConanFile):
    """test_package for mednafen 1.32.1 —— 安装后的 CLI 真跑 + 输出断言。

    mednafen 是 application 包（唯一交付物 bin/mednafen）。conan-init 生成的
    空壳 test.c（只 printf 后 return 0）证不到任何东西，PF3/R34 必拦 —— 换成
    test.sh 的真断言；本 test_package 内不存在第二条测试入口。

    ⚠ mednafen 没有 `--version`，且 `--help` 的退出码是 **255 不是 0**
      （src/drivers/main.cpp:974-986 的 ShowCLHelp 分支 → main.cpp:2408-2414
       `return -1`）。所以 test.sh 对 `--help` 断言的是**输出内容**而不是退出码，
      只在负控制上使用退出码语义。判据与证据的完整说明见 test.sh 文件头。

    断言条数不写死：由 _count_assertions() 从同目录 test.sh 现数
    （run_help / run / grep_check / grep_absent / file_check 各计 1 条），保证
    HMBS_TEST_PACKAGE_RESULT.discovered 与实跑 harness 同源。

    passedCount 口径：test.sh 自累计 FAILED，非零即 exit 1 ⇒ conan 这一层
    「脚本正常返回」等价于「全部断言通过」；失败则记 0。
    """
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    _ASSERTION_RE = re.compile(r"^(?:run_help|run|grep_check|grep_absent|file_check)\s")

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _count_assertions(self):
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test.sh")
        total = 0
        with open(script, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if self._ASSERTION_RE.match(line):
                    total += 1
        if total == 0:
            raise Exception("no assertions found in " + script)
        return total

    def test(self):
        # OHOS：/system/bin/sh (mksh) 不能执行 ELF，用工具链里确认存在的 bash 包装
        # （同 archives/a/adcli/0.9.2/test_package 与 archives/v/vcdimager/2.0.1 的处置）。
        bash = "/data/service/hnp/bin/bash"
        if not os.path.exists(bash):
            bash = os.environ.get("CONFIG_SHELL", "sh")
        command = bash + " test.sh"
        discovered = self._count_assertions()
        result = {"executed": True, "passed": False, "command": command,
                  "discovered": discovered, "passedCount": 0}
        try:
            self.run(command, env="conanrun")
        except Exception:
            self.output.info("HMBS_TEST_PACKAGE_RESULT="
                             + json.dumps(result, ensure_ascii=False))
            raise
        result["passed"] = True
        result["passedCount"] = discovered
        self.output.info("HMBS_TEST_PACKAGE_RESULT="
                         + json.dumps(result, ensure_ascii=False))
