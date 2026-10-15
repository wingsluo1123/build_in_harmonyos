/**
 * TestApacheJMeter — jakarta-jmeter 2.13 消费者验证
 *
 * 以消费者视角用反射断言打包出的 JMeter 核心 API 完整可用、版本正确。
 * 仅使用 JDK 反射（Class.forName + getMethod + 静态调用），编译期不依赖被测 JAR。
 * classpath 由 test.sh 组装（bin/ApacheJMeter.jar + lib/*.jar + lib/ext/*.jar）。
 *
 * 注意：类存在性断言一律用 Class.forName(name, false, cl)（不触发静态初始化）——
 * SaveService 的 <clinit> 会初始化 xstream 1.4.8，在 JDK 17 需消费侧 --add-opens
 * 旗标（已在 notes.md 如实记录，属上游依赖决策）；包内类的存在与可解析性不受影响。
 * 行为断言只保留实测无静态初始化副作用的方法（getJMeterVersion/引擎实例化等）。
 */
public class TestApacheJMeter {

    private static int passed = 0;

    private static void ok(String msg) {
        passed++;
        System.out.println("OK[" + passed + "]: " + msg);
    }

    private static void fail(String msg) {
        System.err.println("FAIL: " + msg);
        System.exit(1);
    }

    private static Class<?> load(String name) throws Exception {
        Class<?> c = Class.forName(name, false, TestApacheJMeter.class.getClassLoader());
        ok("class present: " + name);
        return c;
    }

    @SuppressWarnings("unchecked")
    public static void main(String[] args) throws Exception {
        Class<?>[] none = new Class<?>[0];
        Class<?>[] stringArg = new Class<?>[]{String.class};

        // 核心类型存在（引擎 / 采样器 API / 线程上下文 / 工具 / CLI 入口 / 测试计划数据结构）
        Class<?> jmeter = load("org.apache.jmeter.JMeter");
        load("org.apache.jmeter.engine.StandardJMeterEngine");
        Class<?> sampleResult = load("org.apache.jmeter.samplers.SampleResult");
        load("org.apache.jmeter.threads.JMeterContextService");
        Class<?> jmeterUtils = load("org.apache.jmeter.util.JMeterUtils");
        load("org.apache.jmeter.save.SaveService"); // xstream 初始化见类注释
        load("org.apache.jorphan.collections.HashTree");

        // 引擎契约：StandardJMeterEngine 可实例化（无 GUI 依赖，静态初始化副作用已实测安全）
        Object engine = Class.forName("org.apache.jmeter.engine.StandardJMeterEngine")
                .getConstructor().newInstance();
        if (engine == null) {
            fail("StandardJMeterEngine could not be instantiated");
        }
        ok("StandardJMeterEngine instantiated (headless-safe)");

        // 版本断言：JMeterUtils.getJMeterVersion() 报告 2.13
        String version = (String) jmeterUtils.getMethod("getJMeterVersion", none).invoke(null);
        if (version == null || !version.startsWith("2.13")) {
            fail("getJMeterVersion() = " + version + ", expected to start with 2.13");
        }
        ok("getJMeterVersion() = " + version);

        // 版权断言：JMeterUtils.getJMeterCopyright() 含 Apache
        String copyright = (String) jmeterUtils.getMethod("getJMeterCopyright", none).invoke(null);
        if (copyright == null || !copyright.contains("Apache")) {
            fail("getJMeterCopyright() = " + copyright + ", expected to contain Apache");
        }
        ok("getJMeterCopyright() contains Apache");

        // 采样器 API 契约：SampleResult.setSampleLabel(String)/getSampleLabel()
        sampleResult.getMethod("setSampleLabel", stringArg);
        sampleResult.getMethod("getSampleLabel", none);
        ok("SampleResult exposes setSampleLabel(String)/getSampleLabel()");

        // CLI 入口契约：启动器 NewDriver（ApacheJMeter.jar 的 Main-Class）
        // 提供 public static void main(String[])
        Class.forName("org.apache.jmeter.NewDriver", false,
                TestApacheJMeter.class.getClassLoader())
                .getMethod("main", new Class<?>[]{String[].class});
        ok("NewDriver (Main-Class) exposes public static main(String[])");

        System.out.println("PASS: jakarta-jmeter 2.13 — " + passed + " assertions passed");
    }
}
