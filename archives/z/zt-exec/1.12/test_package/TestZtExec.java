import org.zeroturnaround.exec.ProcessExecutor;
import org.zeroturnaround.exec.ProcessResult;

import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

/**
 * TestZtExec — zt-exec API 调用测试（OHOS 真机消费者验证）。
 *
 * 通过 ProcessExecutor 真实 spawn 子 JVM 进程，覆盖：
 *   1. 同步 execute() + redirectErrorStream(true) + readOutput(true)
 *   2. ProcessResult 退出码与输出捕获
 *   3. exitValues(0) 合法退出码校验
 *   4. start() + getFuture() 异步 API
 *   5. timeout() 超时销毁真实长跑进程
 */
public class TestZtExec {

    private static int passed = 0;

    private static void check(boolean ok, String what) {
        if (!ok) {
            System.err.println("FAIL: " + what);
            System.exit(1);
        }
        passed++;
        System.out.println("OK(" + passed + "): " + what);
    }

    public static void main(String[] args) throws Exception {
        String tmpDir = args[0];

        // 断言 1+2: 同步执行 java -version，合并 stderr 到 stdout 并读取输出
        ProcessResult r = new ProcessExecutor().command("java", "-version")
                .redirectErrorStream(true).readOutput(true).execute();
        check(r.getExitValue() == 0, "java -version exits 0 via ProcessExecutor.execute()");
        check(r.outputUTF8().contains("version"),
                "child stdout/stderr captured via readOutput+redirectErrorStream");

        // 断言 3: exitValues(0) 显式校验合法退出码（非法码会抛 InvalidExitValueException）
        new ProcessExecutor().command("java", "-version").exitValues(0).execute();
        check(true, "exitValues(0) accepted");

        // 断言 4: 异步 start() + Future API
        ProcessResult f = new ProcessExecutor().command("java", "-version")
                .redirectErrorStream(true).readOutput(true)
                .start().getFuture().get(120, TimeUnit.SECONDS);
        check(f.getExitValue() == 0, "start().getFuture().get() async API works");

        // 断言 5: 超时销毁真实长跑进程（Sleeper 睡 30s，1s 超时必须抛 TimeoutException）
        try {
            new ProcessExecutor().command("java", "-cp", tmpDir, "Sleeper", "30")
                    .timeout(1, TimeUnit.SECONDS).execute();
            System.err.println("FAIL: TimeoutException expected for Sleeper(30s) with 1s timeout");
            System.exit(1);
        } catch (TimeoutException e) {
            check(true, "timeout(1s) destroyed long-running child (TimeoutException raised)");
        }

        System.out.println("PASS: zt-exec ProcessExecutor spawn/read/async/timeout API test ("
                + passed + " checks)");
    }
}

class Sleeper {
    public static void main(String[] args) throws Exception {
        Thread.sleep(Long.parseLong(args[0]) * 1000L);
    }
}
