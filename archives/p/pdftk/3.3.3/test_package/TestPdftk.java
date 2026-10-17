/**
 * TestPdftk - pdftk 3.3.3 consumer verification (substantive, R34).
 *
 * Exercises the packaged pdftk classes for real: version/CLI entry points
 * plus an end-to-end PDF round-trip (write a minimal 1-page PDF, concatenate
 * it with `cat`, read back metadata with `dump_data`).
 *
 * NOTE: the bundled iText PdfWriter.getInstance(Document, OutputStream) does
 * NOT exist in pdftk-java 3.3.3 - upstream comments both overloads out with
 * "ssteward omit" (see java/.../com/lowagie/text/pdf/PdfWriter.java), so any
 * reflection or direct call to that factory fails with NoSuchMethod. The
 * consumer therefore writes the input PDF as plain bytes with a computed
 * xref table instead of going through the removed iText creation API. The
 * bundled Document class is still asserted present (shipped), but not used
 * to build the file.
 *
 * Every check prints exactly one "OK[n]: ..." line; any failure prints
 * "FAIL: ..." and exits nonzero. The trailing "PASS: N assertions passed"
 * line lets test.sh count the real assertions from this program's output.
 */
public class TestPdftk {

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
        Class<?> c = Class.forName(name, false, TestPdftk.class.getClassLoader());
        ok("class present: " + name);
        return c;
    }

    private static String readHeader(java.io.File f, int n) throws Exception {
        java.io.FileInputStream in = new java.io.FileInputStream(f);
        byte[] buf = new byte[n];
        int r = in.read(buf);
        in.close();
        if (r < 5) {
            fail("file too short: " + f);
        }
        return new String(buf, 0, 5, "ISO-8859-1");
    }

    private static void writeMinimalPdf(java.io.File f) throws Exception {
        String content = "BT /F1 24 Tf 100 700 Td (hello pdftk consumer test) Tj ET";
        byte[] contentBytes = content.getBytes("ISO-8859-1");
        String[] objs = new String[5];
        objs[0] = "<< /Type /Catalog /Pages 2 0 R >>";
        objs[1] = "<< /Type /Pages /Kids [3 0 R] /Count 1 >>";
        objs[2] = "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
            + " /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>";
        objs[3] = "<< /Length " + contentBytes.length + " >>\nstream\n"
            + content + "\nendstream";
        objs[4] = "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>";
        java.io.ByteArrayOutputStream buf = new java.io.ByteArrayOutputStream();
        buf.write("%PDF-1.4\n".getBytes("ISO-8859-1"));
        long[] offsets = new long[5];
        for (int i = 0; i < 5; i++) {
            offsets[i] = buf.size();
            buf.write(((i + 1) + " 0 obj\n").getBytes("ISO-8859-1"));
            buf.write(objs[i].getBytes("ISO-8859-1"));
            buf.write("\nendobj\n".getBytes("ISO-8859-1"));
        }
        long xrefPos = buf.size();
        StringBuilder xref = new StringBuilder();
        xref.append("xref\n0 6\n");
        xref.append("0000000000 65535 f \n");
        for (int i = 0; i < 5; i++) {
            xref.append(String.format("%010d 00000 n \n", offsets[i]));
        }
        xref.append("trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n");
        xref.append(xrefPos).append("\n%%EOF\n");
        buf.write(xref.toString().getBytes("ISO-8859-1"));
        java.io.FileOutputStream out = new java.io.FileOutputStream(f);
        buf.writeTo(out);
        out.close();
    }

    public static void main(String[] args) throws Exception {
        Class<?> pdftk = load("com.gitlab.pdftk_java.pdftk");
        load("com.gitlab.pdftk_java.com.lowagie.text.Document");

        // Version constant matches the packaged release.
        // NOTE: upstream declares it as package-private
        // `static final String PDFTK_VER` (see pdftk.java), so Class.getField()
        // (public only) throws NoSuchFieldException; use getDeclaredField.
        java.lang.reflect.Field verField = pdftk.getDeclaredField("PDFTK_VER");
        verField.setAccessible(true);
        String ver = (String) verField.get(null);
        if (!"3.3.3".equals(ver)) {
            fail("PDFTK_VER = " + ver + ", expected 3.3.3");
        }
        ok("PDFTK_VER = " + ver);

        // CLI entry point exists and answers --version with rc 0.
        java.lang.reflect.Method mainNoExit =
            pdftk.getMethod("main_noexit", new Class<?>[]{String[].class});
        ok("main_noexit(String[]) present");
        int rc = ((Integer) mainNoExit.invoke(null, new Object[]{new String[]{"--version"}})).intValue();
        if (rc != 0) {
            fail("--version returned " + rc);
        }
        ok("--version returned 0");

        // Write a minimal valid 1-page PDF directly (see class NOTE: the
        // shaded PdfWriter.getInstance factory was removed upstream).
        java.io.File work = new java.io.File(args.length > 0 ? args[0] : ".");
        java.io.File inPdf = new java.io.File(work, "consumer-in.pdf");
        writeMinimalPdf(inPdf);
        if (!"%PDF-".equals(readHeader(inPdf, 5)) || inPdf.length() == 0) {
            fail("consumer-in.pdf is not a PDF");
        }
        ok("minimal 1-page PDF written (" + inPdf.length() + " bytes)");

        // pdftk cat round-trip: in -> out must be a valid PDF.
        java.io.File outPdf = new java.io.File(work, "consumer-out.pdf");
        rc = ((Integer) mainNoExit.invoke(null, new Object[]{new String[]{
                inPdf.getAbsolutePath(), "cat", "output", outPdf.getAbsolutePath()}})).intValue();
        if (rc != 0) {
            fail("cat returned " + rc);
        }
        ok("cat returned 0");
        if (!outPdf.isFile() || !"%PDF-".equals(readHeader(outPdf, 5)) || outPdf.length() == 0) {
            fail("consumer-out.pdf missing or not a PDF");
        }
        ok("cat output is a valid PDF (" + outPdf.length() + " bytes)");

        // dump_data on the round-tripped file must report one page.
        java.io.ByteArrayOutputStream capture = new java.io.ByteArrayOutputStream();
        java.io.PrintStream orig = System.out;
        System.setOut(new java.io.PrintStream(capture, true, "UTF-8"));
        try {
            rc = ((Integer) mainNoExit.invoke(null, new Object[]{new String[]{
                    outPdf.getAbsolutePath(), "dump_data"}})).intValue();
        } finally {
            System.setOut(orig);
        }
        String dump = capture.toString("UTF-8");
        if (rc != 0 || dump.indexOf("NumberOfPages: 1") < 0) {
            fail("dump_data rc=" + rc + " output=" + dump.trim());
        }
        ok("dump_data reports NumberOfPages: 1");

        System.out.println("PASS: " + passed + " assertions passed");
    }
}
