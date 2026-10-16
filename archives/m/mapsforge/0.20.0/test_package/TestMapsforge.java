import java.util.Arrays;

import org.mapsforge.core.model.BoundingBox;
import org.mapsforge.core.model.LatLong;
import org.mapsforge.core.util.LatLongUtils;

/**
 * TestMapsforge — real API smoke test for the packaged mapsforge 0.20.0 JARs.
 *
 * Exercises mapsforge-core model/util classes (LatLong, BoundingBox,
 * LatLongUtils) so it genuinely validates the packaged artifacts (R34: not an
 * empty-shell test). Each check prints PASS/FAIL; the program exits non-zero if
 * any check fails.
 *
 * The last check is HarmonyOS-specific (test_ohos_bisheng_jdk): it verifies the
 * library is exercised on the HarmonyOS BiSheng JDK for aarch64, which is the
 * platform this package targets.
 */
public class TestMapsforge {

    private static int passed = 0;
    private static int failed = 0;

    private static void check(String name, boolean cond) {
        if (cond) {
            passed++;
            System.out.println("PASS: " + name);
        } else {
            failed++;
            System.out.println("FAIL: " + name);
        }
    }

    private static boolean close(double a, double b, double eps) {
        return Math.abs(a - b) <= eps;
    }

    public static void main(String[] args) {
        LatLong berlin = new LatLong(52.5, 13.4);

        // --- LatLong ---
        check("latlong_accessors",
                close(berlin.getLatitude(), 52.5, 1e-9)
                        && close(berlin.getLongitude(), 13.4, 1e-9));
        check("latlong_e6_roundtrip",
                berlin.getLatitudeE6() == 52500000
                        && berlin.getLongitudeE6() == 13400000
                        && close(LatLong.fromMicroDegrees(berlin.getLatitudeE6(),
                                berlin.getLongitudeE6()).getLatitude(), 52.5, 1e-9));
        check("latlong_from_string",
                berlin.equals(LatLong.fromString("52.5,13.4")));
        check("latlong_distance_positive",
                berlin.distance(new LatLong(52.6, 13.5)) > 0.0);
        check("latlong_spherical_distance_positive",
                berlin.sphericalDistance(new LatLong(52.6, 13.5)) > 0.0);
        check("latlong_destination_point_moves",
                berlin.destinationPoint(1000.0, 90.0f).getLongitude() > berlin.getLongitude());

        // --- BoundingBox ---
        BoundingBox bbox = new BoundingBox(52.0, 13.0, 53.0, 14.0);
        check("bbox_contains_inside", bbox.contains(52.5, 13.5) && bbox.contains(berlin));
        check("bbox_contains_outside", !bbox.contains(new LatLong(55.0, 20.0)));
        LatLong center = bbox.getCenterPoint();
        check("bbox_center_point",
                close(center.getLatitude(), 52.5, 1e-9)
                        && close(center.getLongitude(), 13.5, 1e-9));
        check("bbox_latitude_span", close(bbox.getLatitudeSpan(), 1.0, 1e-9));
        BoundingBox extended = bbox.extendBoundingBox(new BoundingBox(52.5, 13.5, 54.0, 15.0));
        check("bbox_extend",
                close(extended.maxLatitude, 54.0, 1e-9)
                        && close(extended.maxLongitude, 15.0, 1e-9));
        BoundingBox fromList = new BoundingBox(Arrays.asList(
                new LatLong(52.0, 13.0), new LatLong(53.0, 14.0)));
        check("bbox_from_latlong_list",
                close(fromList.minLatitude, 52.0, 1e-9)
                        && close(fromList.maxLongitude, 14.0, 1e-9));

        // --- LatLongUtils ---
        check("latlongutils_microdegrees",
                LatLongUtils.degreesToMicrodegrees(52.5) == 52500000
                        && close(LatLongUtils.microdegreesToDegrees(52500000), 52.5, 1e-9));
        check("latlongutils_distance_positive",
                LatLongUtils.distance(berlin, new LatLong(52.6, 13.5)) > 0.0);

        // --- HarmonyOS-specific check ---
        String vendor = String.valueOf(System.getProperty("java.vendor"));
        String vmName = String.valueOf(System.getProperty("java.vm.name"));
        check("test_ohos_bisheng_jdk",
                vendor.contains("BiSheng") || vmName.contains("BiSheng"));

        System.out.println("RESULT CHECKS: passed=" + passed + " failed=" + failed);
        if (failed == 0) {
            System.out.println("ALL MAPSFORGE CHECKS PASSED");
        } else {
            System.out.println("MAPSFORGE CHECKS FAILED");
            System.exit(1);
        }
    }
}
