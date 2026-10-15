import java.io.File;
import java.nio.file.Files;
import java.nio.file.Path;

import app.tuxguitar.util.TGUserFileUtils;

/**
 * HarmonyOS-specific consumer test (>= 1 case required by the task).
 *
 * TuxGuitar resolves its per-user application directory from os.name
 * (TGUserFileUtils.getDefaultUserAppDir): macOS -> ~/Library/Application Support,
 * Windows -> ~/AppData/Roaming, everything else -> ~/.config. The dynamic
 * "everything else" branch is the one HarmonyOS takes, and it must actually
 * produce a creatable/usable directory on this platform.
 */
public class TestHarmonyOSPlatform {

    private static int passed = 0;
    private static int failed = 0;

    private static void check(String name, boolean ok, String detail) {
        if (ok) {
            passed++;
            System.out.println("TEST PASS  " + name + (detail.isEmpty() ? "" : "  (" + detail + ")"));
        } else {
            failed++;
            System.out.println("TEST FAIL  " + name + (detail.isEmpty() ? "" : "  (" + detail + ")"));
        }
    }

    public static void main(String[] args) throws Exception {
        System.out.println("== TuxGuitar HarmonyOS platform test ==");
        String osName = System.getProperty("os.name");
        String osArch = System.getProperty("os.arch");
        System.out.println("os.name=" + osName + " os.arch=" + osArch
                + " java.version=" + System.getProperty("java.version"));

        // OHOS-1: the JVM really reports HarmonyOS (this is the platform the package targets)
        check("ohos.osNameIsHarmonyOS", "HarmonyOS".equals(osName), "os.name=" + osName);

        // OHOS-2: TuxGuitar takes its portable (non-macOS/non-Windows) branch on HarmonyOS
        check("ohos.userDirUsesPortableBranch",
                TGUserFileUtils.PATH_USER_DIR.replace('\\', '/').endsWith(".config/tuxguitar"),
                "PATH_USER_DIR=" + TGUserFileUtils.PATH_USER_DIR);

        // OHOS-2b: the directory must be absolute — the JVM on HarmonyOS reports
        // user.home as an unusable placeholder ("?"), so TuxGuitar must fall back
        // to the POSIX HOME variable instead of resolving next to the CWD.
        check("ohos.userDirIsAbsolute",
                new File(TGUserFileUtils.PATH_USER_DIR).isAbsolute(),
                "PATH_USER_DIR=" + TGUserFileUtils.PATH_USER_DIR);

        // OHOS-2c: it must land under HOME (regression guard for the broken user.home)
        String envHome = System.getenv("HOME");
        check("ohos.userDirUnderHome",
                envHome != null && TGUserFileUtils.PATH_USER_DIR.startsWith(envHome),
                "HOME=" + envHome + " PATH_USER_DIR=" + TGUserFileUtils.PATH_USER_DIR);

        // OHOS-3: that directory is really usable (created + writable on this platform)
        Path userDir = new File(TGUserFileUtils.PATH_USER_DIR).toPath();
        boolean usable = Files.isDirectory(userDir) && Files.isWritable(userDir);
        File probe = new File(userDir.toFile(), ".ohos-write-probe");
        boolean wrote = probe.createNewFile() || probe.exists();
        boolean deleted = wrote && probe.delete();
        check("ohos.userDirWritable", usable && wrote && deleted,
                "dir=" + userDir + " wrote=" + wrote + " cleaned=" + deleted);

        System.out.println("OHOS TEST SUMMARY: passed=" + passed + " failed=" + failed);
        if (failed > 0) {
            System.exit(1);
        }
    }
}
