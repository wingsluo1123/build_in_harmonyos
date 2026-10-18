/*
 * Consumer test for the packaged typometer 1.0.1 uber-JAR.
 *
 * It exercises real public API of the packaged library (R34) and is fully
 * self-contained — no external fixtures (binary reference screenshots) are
 * committed or required:
 *   1. loads the packaged entry point and core classes,
 *   2. statistics: SummaryStatistics.analyze() over a known sample,
 *   3. chart: Series / ChartData aggregation,
 *   4. statistics: FrequencyDistribution.compute() over a known series,
 *   5. HarmonyOS platform detection (ScreenAccessor.isHarmonyOS /
 *      isNativeApiSupported).
 *
 * Usage: java TestTypometer [--require-harmonyos]
 *
 *   --require-harmonyos   Enforce the HarmonyOS-specific assertions
 *                         (isHarmonyOS() == true and
 *                         isNativeApiSupported() == false). Passed by
 *                         test_package/conanfile.py under settings.os == "OHOS".
 *
 * Any other argument is ignored.
 */
import com.pavelfatin.typometer.chart.ChartData;
import com.pavelfatin.typometer.chart.Series;
import com.pavelfatin.typometer.screen.ScreenAccessor;
import com.pavelfatin.typometer.statistics.FrequencyDistribution;
import com.pavelfatin.typometer.statistics.Statistics;
import com.pavelfatin.typometer.statistics.SummaryStatistics;

import java.awt.Color;
import java.util.Arrays;
import java.util.Collection;
import java.util.List;

public class TestTypometer {
    private static final double EPSILON = 1.0e-9D;

    private static int passed = 0;
    private static int failed = 0;

    private static void check(String name, boolean condition) {
        if (condition) {
            passed++;
            System.out.println("  PASS: " + name);
        } else {
            failed++;
            System.out.println("  FAIL: " + name);
        }
    }

    private static boolean near(double actual, double expected) {
        return Math.abs(actual - expected) < EPSILON;
    }

    public static void main(String[] args) throws Exception {
        boolean requireHarmonyOS = false;
        for (String arg : args) {
            if ("--require-harmonyos".equals(arg)) {
                requireHarmonyOS = true;
            }
        }

        System.out.println("[1] packaged class loading");
        check("entry point com.pavelfatin.typometer.Application loads",
                Class.forName("com.pavelfatin.typometer.Application") != null);
        check("core class com.pavelfatin.typometer.metrics.Metrics loads",
                Class.forName("com.pavelfatin.typometer.metrics.Metrics") != null);
        check("statistics class com.pavelfatin.typometer.statistics.SummaryStatistics loads",
                Class.forName("com.pavelfatin.typometer.statistics.SummaryStatistics") != null);

        System.out.println("[2] statistics: SummaryStatistics.analyze()");
        List<Double> sample = Arrays.asList(1.0D, 2.0D, 3.0D, 4.0D, 5.0D);
        Statistics stats = SummaryStatistics.analyze(sample);
        check("count == 5", stats.getCount() == 5);
        check("min == 1.0", near(stats.getMin(), 1.0D));
        check("max == 5.0", near(stats.getMax(), 5.0D));
        // Upstream SummaryStatistics.getRange() returns (min - max), i.e. -4.0 here.
        check("range == min - max == -4.0", near(stats.getRange(), -4.0D));
        check("mean == 3.0", near(stats.getMean(), 3.0D));

        System.out.println("[3] chart: Series / ChartData");
        Series s1 = new Series("a", Color.RED, Arrays.asList(1.0D, 2.0D, 3.0D));
        Series s2 = new Series("b", Color.BLUE, Arrays.asList(4.0D, 5.0D));
        ChartData chart = new ChartData(Arrays.asList("c1", "c2"), Arrays.asList(s1, s2));
        check("series length == 3", s1.getLength() == 3);
        check("series max value == 5.0", near(s2.getMaxValue(), 5.0D));
        check("chart category count == 2", chart.getCategoryCount() == 2);
        check("chart max length == 3", chart.getMaxLength() == 3);
        check("chart max value == 5.0", near(chart.getMaxValue(), 5.0D));

        System.out.println("[4] statistics: FrequencyDistribution.compute()");
        Collection<Collection<Double>> series = Arrays.asList(
                Arrays.asList(1.0D, 2.0D, 3.0D, 4.0D),
                Arrays.asList(2.0D, 3.0D, 4.0D, 5.0D));
        FrequencyDistribution distribution = FrequencyDistribution.compute(series, 2);
        check("distribution has ranges", distribution.getRanges() != null
                && !distribution.getRanges().isEmpty());
        check("distribution has frequencies", distribution.getFrequencies() != null
                && !distribution.getFrequencies().isEmpty());
        check("frequencies row count == series count",
                distribution.getFrequencies().size() == series.size());

        System.out.println("[5] HarmonyOS platform detection");
        System.out.println("  info: os.name = " + System.getProperty("os.name"));
        System.out.println("  info: ScreenAccessor.isHarmonyOS() = " + ScreenAccessor.isHarmonyOS());
        System.out.println("  info: ScreenAccessor.isNativeApiSupported() = "
                + ScreenAccessor.isNativeApiSupported());
        check("HarmonyOS platform detected via os.name", ScreenAccessor.isHarmonyOS());

        if (requireHarmonyOS) {
            System.out.println("[6] HarmonyOS-specific assertions");
            check("OS is HarmonyOS", ScreenAccessor.isHarmonyOS());
            check("native X11/WinAPI screen access is disabled on HarmonyOS",
                    !ScreenAccessor.isNativeApiSupported());
        }

        System.out.println("TEST SUMMARY: " + passed + " passed, " + failed + " failed");
        if (failed > 0) {
            System.exit(1);
        }
    }
}
