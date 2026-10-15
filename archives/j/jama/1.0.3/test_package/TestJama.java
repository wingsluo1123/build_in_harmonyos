import Jama.CholeskyDecomposition;
import Jama.EigenvalueDecomposition;
import Jama.LUDecomposition;
import Jama.Matrix;
import Jama.QRDecomposition;
import Jama.SingularValueDecomposition;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;
import java.io.FileWriter;
import java.io.PrintWriter;
import java.io.StringReader;
import java.io.StringWriter;
import java.text.DecimalFormat;
import java.text.DecimalFormatSymbols;
import java.util.ArrayList;
import java.util.Enumeration;
import java.util.List;
import java.util.Locale;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;

/**
 * TestJama — consumer-side verification of the packaged jama-1.0.3.jar on
 * HarmonyOS PC (aarch64).
 *
 * Two groups of real checks (R34 — every assertion calls the library):
 *
 * <ul>
 *   <li>{@code API-xx} — numeric assertions on the JAMA API surface:
 *       {@link Matrix} arithmetic/access, {@link LUDecomposition},
 *       {@link QRDecomposition}, {@link CholeskyDecomposition},
 *       {@link SingularValueDecomposition}, {@link EigenvalueDecomposition},
 *       and the upstream {@code print}/{@code read} round trip.</li>
 *   <li>{@code OHOS-x} — HarmonyOS consumer-feasibility checks: the JAR runs on
 *       the HarmonyOS aarch64 JVM, is discovered through the Conan package
 *       layout, performs real file I/O without assuming a writable {@code /tmp},
 *       and ships platform-neutral bytecode only.</li>
 * </ul>
 *
 * Output contract (parsed by test.sh):
 * {@code PASS: <id> | <what> | <detail>} / {@code FAIL: ...} per check, then
 * {@code RESULT CHECKS: passed=N failed=M total=T}; exit code 1 if any check
 * fails.
 */
public final class TestJama {

    private static int passed = 0;
    private static final List<String> failed = new ArrayList<String>();

    private static final double EPS = 1e-9;

    private TestJama() {
    }

    // ── helpers ────────────────────────────────────────────────────────────
    private static void check(String id, String what, boolean ok, String detail) {
        if (ok) {
            passed++;
            System.out.println("PASS: " + id + " | " + what + " | " + detail);
        } else {
            failed.add(id);
            System.out.println("FAIL: " + id + " | " + what + " | " + detail);
        }
    }

    private static boolean close(double a, double b) {
        return Math.abs(a - b) <= EPS * Math.max(1.0, Math.max(Math.abs(a), Math.abs(b)));
    }

    private static boolean matClose(Matrix m, double[][] expected) {
        if (m.getRowDimension() != expected.length
                || m.getColumnDimension() != expected[0].length) {
            return false;
        }
        for (int i = 0; i < expected.length; i++) {
            for (int j = 0; j < expected[0].length; j++) {
                if (!close(m.get(i, j), expected[i][j])) {
                    return false;
                }
            }
        }
        return true;
    }

    private static boolean matClose(Matrix m, Matrix expected) {
        if (m.getRowDimension() != expected.getRowDimension()
                || m.getColumnDimension() != expected.getColumnDimension()) {
            return false;
        }
        for (int i = 0; i < m.getRowDimension(); i++) {
            for (int j = 0; j < m.getColumnDimension(); j++) {
                if (!close(m.get(i, j), expected.get(i, j))) {
                    return false;
                }
            }
        }
        return true;
    }

    private static String fmt(Matrix m) {
        StringBuilder sb = new StringBuilder("[");
        for (int i = 0; i < m.getRowDimension(); i++) {
            if (i > 0) {
                sb.append(", ");
            }
            sb.append("[");
            for (int j = 0; j < m.getColumnDimension(); j++) {
                if (j > 0) {
                    sb.append(", ");
                }
                sb.append(String.format(Locale.US, "%.10g", m.get(i, j)));
            }
            sb.append("]");
        }
        return sb.append("]").toString();
    }

    public static void main(String[] args) throws Exception {
        // Upstream sample matrices (same values the upstream TestMatrix uses:
        // avals is 3x4, norm1=33, normInf=30, normF=sqrt(650), trace=15).
        double[][] avals = {{1., 4., 7., 10.}, {2., 5., 8., 11.}, {3., 6., 9., 12.}};
        Matrix A = new Matrix(avals);

        // ── API-01..05: construction and access ───────────────────────────
        check("API-01", "Matrix.getRowDimension", A.getRowDimension() == 3,
                "rows=" + A.getRowDimension());
        check("API-02", "Matrix.getColumnDimension", A.getColumnDimension() == 4,
                "cols=" + A.getColumnDimension());
        check("API-03", "Matrix.get(2,3) == 12", close(A.get(2, 3), 12.0),
                "A(2,3)=" + A.get(2, 3));

        double[][] copy = A.getArrayCopy();
        copy[0][0] = -999.0;
        check("API-04", "Matrix.getArrayCopy is a detached copy",
                close(A.get(0, 0), 1.0), "A(0,0)=" + A.get(0, 0) + " after mutating copy");

        Matrix I = Matrix.identity(3, 4);
        double[][] eye = {{1., 0., 0., 0.}, {0., 1., 0., 0.}, {0., 0., 1., 0.}};
        check("API-05", "Matrix.identity(3,4)", matClose(I, eye), "I=" + fmt(I));

        // ── API-06..11: arithmetic and norms ──────────────────────────────
        Matrix B = new Matrix(new double[][] {{1., 1., 1., 1.}, {1., 1., 1., 1.}, {1., 1., 1., 1.}});
        double[][] plusMinus = {{2., 5., 8., 11.}, {3., 6., 9., 12.}, {4., 7., 10., 13.}};
        check("API-06", "Matrix.plus / minus",
                matClose(A.plus(B), plusMinus) && matClose(A.plus(B).minus(B), avals),
                "A+B=" + fmt(A.plus(B)));

        Matrix T = A.transpose();
        double[][] tvals = {{1., 2., 3.}, {4., 5., 6.}, {7., 8., 9.}, {10., 11., 12.}};
        check("API-07", "Matrix.transpose", matClose(T, tvals), "A^T=" + fmt(T));

        Matrix P = new Matrix(new double[][] {{4., 1., 1.}, {1., 2., 3.}, {1., 3., 6.}});
        double[][] p2 = {{9., 27., 45., 63.}, {14., 32., 50., 68.}, {25., 55., 85., 115.}};
        check("API-08", "Matrix.times(Matrix)", matClose(P.times(A), p2), "P*A=" + fmt(P.times(A)));

        check("API-09", "Matrix.norm1 / normInf / normF / trace",
                close(A.norm1(), 33.0) && close(A.normInf(), 30.0)
                        && close(A.normF(), Math.sqrt(650.0)) && close(A.trace(), 15.0),
                "norm1=" + A.norm1() + " normInf=" + A.normInf()
                        + " normF=" + A.normF() + " trace=" + A.trace());

        // ── API-10..15: LU decomposition ──────────────────────────────────
        Matrix S = new Matrix(new double[][] {{4., 3.}, {6., 3.}});
        Matrix b = new Matrix(new double[][] {{10.}, {12.}});
        LUDecomposition lu = S.lu();
        check("API-10", "Matrix.det (LU based) == -6", close(S.det(), -6.0), "det=" + S.det());
        check("API-11", "LUDecomposition.isNonsingular", lu.isNonsingular(),
                "isNonsingular=" + lu.isNonsingular());
        check("API-12", "LUDecomposition.det == -6", close(lu.det(), -6.0), "det=" + lu.det());
        check("API-13", "LUDecomposition.solve: [[4,3],[6,3]]x=[10,12] -> [1,2]",
                matClose(lu.solve(b), new double[][] {{1.}, {2.}}),
                "x=" + fmt(lu.solve(b)));

        Matrix L = lu.getL();
        Matrix U = lu.getU();
        boolean triangular = close(L.get(0, 0), 1.0) && close(L.get(0, 1), 0.0)
                && close(U.get(1, 0), 0.0) && !close(U.get(0, 0), 0.0);
        check("API-14", "LUDecomposition.getL is unit lower / getU upper triangular",
                triangular, "L=" + fmt(L) + " U=" + fmt(U));
        check("API-15", "Matrix.solve(Matrix) agrees with LUDecomposition.solve",
                matClose(S.solve(b), lu.solve(b)), "S.solve(b)=" + fmt(S.solve(b)));

        // ── API-16..19: QR decomposition ──────────────────────────────────
        Matrix Q = new Matrix(new double[][] {{1., 1.}, {1., 2.}, {1., 3.}});
        Matrix qb = new Matrix(new double[][] {{1.}, {2.}, {2.}});
        QRDecomposition qr = Q.qr();
        check("API-16", "QRDecomposition.isFullRank", qr.isFullRank(),
                "isFullRank=" + qr.isFullRank());
        check("API-17", "QRDecomposition.solve (least squares) == [2/3, 1/2]",
                matClose(qr.solve(qb), new double[][] {{2.0 / 3.0}, {0.5}}),
                "x=" + fmt(qr.solve(qb)));

        Matrix qq = qr.getQ();
        double[][] q2q = qq.transpose().times(qq).getArrayCopy();
        boolean orthonormal = close(q2q[0][0], 1.0) && close(q2q[1][1], 1.0)
                && close(q2q[0][1], 0.0) && close(q2q[1][0], 0.0);
        check("API-18", "QRDecomposition.getQ is orthonormal (Q^T Q == I)",
                orthonormal, "Q^T Q=" + fmt(qq.transpose().times(qq)));

        Matrix r = qr.getR();
        check("API-19", "QRDecomposition.getR upper triangular and Q*R == A",
                close(r.get(1, 0), 0.0) && matClose(qq.times(r), Q),
                "R=" + fmt(r) + " Q*R=" + fmt(qq.times(r)));

        // ── API-20..22: Cholesky decomposition ────────────────────────────
        Matrix spd = new Matrix(new double[][] {{4., 2.}, {2., 3.}});
        Matrix spdb = new Matrix(new double[][] {{6.}, {5.}});
        CholeskyDecomposition chol = spd.chol();
        check("API-20", "CholeskyDecomposition.isSPD", chol.isSPD(),
                "isSPD=" + chol.isSPD());
        check("API-21", "CholeskyDecomposition.solve: [[4,2],[2,3]]x=[6,5] -> [1,1]",
                matClose(chol.solve(spdb), new double[][] {{1.}, {1.}}),
                "x=" + fmt(chol.solve(spdb)));
        check("API-22", "CholeskyDecomposition.getL == [[2,0],[1,sqrt(2)]]",
                matClose(chol.getL(),
                        new double[][] {{2., 0.}, {1., Math.sqrt(2.0)}}),
                "L=" + fmt(chol.getL()));

        // ── API-23..24: singular value decomposition ──────────────────────
        Matrix diag = new Matrix(new double[][] {{3., 0.}, {0., 2.}});
        SingularValueDecomposition svd = diag.svd();
        double[] singular = svd.getSingularValues();
        check("API-23", "SingularValueDecomposition.getSingularValues == [3,2]",
                singular.length == 2 && close(singular[0], 3.0) && close(singular[1], 2.0),
                "s=" + singular[0] + "," + singular[1]);
        check("API-24", "SingularValueDecomposition norm2/rank/cond of diag(3,2)",
                close(svd.norm2(), 3.0) && svd.rank() == 2 && close(svd.cond(), 1.5),
                "norm2=" + svd.norm2() + " rank=" + svd.rank() + " cond=" + svd.cond());

        // ── API-25..27: eigenproblem and I/O round trip ───────────────────
        Matrix sym = new Matrix(new double[][] {{2., 1.}, {1., 2.}});
        EigenvalueDecomposition eig = sym.eig();
        double[] real = eig.getRealEigenvalues();
        double lo = Math.min(real[0], real[1]);
        double hi = Math.max(real[0], real[1]);
        check("API-25", "EigenvalueDecomposition of [[2,1],[1,2]] == {1,3}",
                real.length == 2 && close(lo, 1.0) && close(hi, 3.0),
                "eigenvalues=" + real[0] + "," + real[1]);
        check("API-26", "EigenvalueDecomposition.getD diagonal == eigenvalues",
                close(eig.getD().get(0, 0), real[0]) && close(eig.getD().get(1, 1), real[1]),
                "D=" + fmt(eig.getD()));

        DecimalFormat fmtUs = new DecimalFormat("0.0000E00");
        fmtUs.setDecimalFormatSymbols(new DecimalFormatSymbols(Locale.US));
        StringWriter sink = new StringWriter();
        PrintWriter writer = new PrintWriter(sink);
        S.print(writer, fmtUs, 10);
        writer.close();
        Matrix reread = Matrix.read(new BufferedReader(new StringReader(sink.toString())));
        check("API-27", "Matrix.print / Matrix.read round trip (< 0.001)",
                S.minus(reread).norm1() < 0.001,
                "norm1(A - read(print(A)))=" + S.minus(reread).norm1());

        // ══ HarmonyOS consumer checks (the OHOS cases) ════════════════════
        String osName = System.getProperty("os.name", "");
        String osArch = System.getProperty("os.arch", "");
        String osVersion = System.getProperty("os.version", "");
        String javaVendor = System.getProperty("java.vendor", "");
        String javaVersion = System.getProperty("java.version", "");
        String jarFromEnv = System.getenv("JAMA_JAR");

        // OHOS-1: the packaged JAR really runs on the HarmonyOS aarch64 JVM.
        check("OHOS-1", "HarmonyOS aarch64 JVM",
                "HarmonyOS".equals(osName) && "aarch64".equals(osArch)
                        && javaVersion.startsWith("17.")
                        && "BiSheng".equals(javaVendor),
                "os.name=" + osName + " os.arch=" + osArch + " os.version=" + osVersion
                        + " java=" + javaVersion + "/" + javaVendor);

        // OHOS-2: the artifact produced by `conan create` is discoverable
        //         through the Conan package layout and is the JAR in use.
        String codeSource = "";
        try {
            java.security.CodeSource cs =
                    Matrix.class.getProtectionDomain().getCodeSource();
            if (cs != null && cs.getLocation() != null) {
                codeSource = new File(cs.getLocation().toURI()).getAbsolutePath();
            }
        } catch (Exception e) {
            codeSource = "unresolved: " + e;
        }
        boolean jarMatches = jarFromEnv != null && !jarFromEnv.isEmpty()
                && new File(jarFromEnv).isFile()
                && codeSource.endsWith(new File(jarFromEnv).getName())
                && MatricesLoadedFromJar();
        check("OHOS-2", "packaged JAR consumed via Conan layout (JAMA_JAR)",
                jarMatches,
                "JAMA_JAR=" + jarFromEnv + " codeSource=" + codeSource);

        // OHOS-3: real file I/O on the HarmonyOS filesystem.  HarmonyOS has no
        //         writable /tmp, so the consumer must work from a writable
        //         working directory; test.sh runs this class in one.
        String cwd = new File(".").getCanonicalPath();
        File scratch = new File(cwd, "jama-io-check.out");
        boolean ioOk;
        String ioDetail;
        try {
            PrintWriter file = new PrintWriter(new FileWriter(scratch));
            S.print(file, fmtUs, 10);
            file.close();
            Matrix fromFile = Matrix.read(new BufferedReader(new FileReader(scratch)));
            ioOk = S.minus(fromFile).norm1() < 0.001;
            ioDetail = "cwd=" + cwd + " file=" + scratch.getName()
                    + " size=" + scratch.length() + " chars, norm1(diff)="
                    + S.minus(fromFile).norm1();
        } catch (Exception e) {
            ioOk = false;
            ioDetail = "cwd=" + cwd + " error=" + e;
        } finally {
            scratch.delete();
        }
        check("OHOS-3", "matrix file I/O in a writable HarmonyOS working directory "
                + "(no reliance on writable /tmp)", ioOk, ioDetail);

        // OHOS-4: the packaged JAR is platform-neutral bytecode only, which is
        //         why the very same artifact is consumable on OHOS aarch64.
        //         META-INF/ (manifest) is normal JAR metadata, not code.
        boolean bytecodeOnly = false;
        int classCount = 0;
        int metadataCount = 0;
        String auditDetail = "JAMA_JAR not set";
        if (jarFromEnv != null && new File(jarFromEnv).isFile()) {
            ZipFile zip = new ZipFile(jarFromEnv);
            try {
                bytecodeOnly = true;
                Enumeration<? extends ZipEntry> entries = zip.entries();
                while (entries.hasMoreElements()) {
                    ZipEntry entry = entries.nextElement();
                    if (entry.isDirectory()) {
                        continue;
                    }
                    String name = entry.getName();
                    if (name.startsWith("META-INF/")) {
                        metadataCount++;
                        continue;
                    }
                    classCount++;
                    if (!name.endsWith(".class")) {
                        bytecodeOnly = false;
                    }
                }
            } finally {
                zip.close();
            }
            auditDetail = "classes=" + classCount + " metadata=" + metadataCount
                    + " (no native code entries)";
        }
        check("OHOS-4", "packaged JAR is platform-neutral bytecode",
                bytecodeOnly && classCount > 0, auditDetail);

        int total = passed + failed.size();
        System.out.println("RESULT CHECKS: passed=" + passed + " failed=" + failed.size()
                + " total=" + total
                + (failed.isEmpty() ? "" : " failed_ids=" + failed));
        if (!failed.isEmpty()) {
            System.exit(1);
        }
        System.out.println("ALL JAMA CHECKS PASSED");
    }

    /** True when Jama.Matrix actually comes out of the packaged JAR file. */
    private static boolean MatricesLoadedFromJar() {
        String resource = "/" + Matrix.class.getName().replace('.', '/') + ".class";
        return Matrix.class.getResource(resource) != null
                && "jar".equalsIgnoreCase(Matrix.class.getResource(resource).getProtocol());
    }
}
