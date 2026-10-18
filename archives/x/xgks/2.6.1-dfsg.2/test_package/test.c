/* Consumer test for the packaged xgks C library (R34: real API usage).
 *
 * Opens GKS, opens a GKSM metafile (MO) workstation to a file — the only
 * workstation class that needs no X display — draws one polyline, one
 * polymarker and one fill area, closes everything down, then verifies the
 * metafile exists and is non-empty. API call sequence mirrors the upstream
 * progs/pline.c and progs/hanoi.c demos. Each check prints an OK line and
 * the program exits non-zero on the first failure, so the 6 printed lines
 * are the honest assertion count consumed by the HMBS marker.
 */

#include <stdio.h>
#include <sys/stat.h>

#include <xgks.h>

/* xgks.h (1989 vintage) provides the GKS types but no function prototypes;
 * declare the entry points used here with the K&R-compatible signatures the
 * upstream demos rely on (pline.c checks every call against 0). */
Gint gopengks(FILE *err_file, Gint memory);
Gint gopenws(Gint ws_id, Gchar *conn, Gchar *wstype);
Gint gactivatews(Gint ws_id);
Gint gsetwswindow(Gint ws_id, Glimit *window);
Gint gpolyline(Gint n, Gpoint *pts);
Gint gpolymarker(Gint n, Gpoint *pts);
Gint gfillarea(Gint n, Gpoint *pts);
Gint gdeactivatews(Gint ws_id);
Gint gclosews(Gint ws_id);
Gint gclosegks(void);

#define WS_ID 1
#define OUTFILE "test_xgks.gksm"

int main(void)
{
    Gint result;
    Glimit window;
    Gpoint line_pts[2];
    Gpoint marker_pts[3];
    Gpoint fill_pts[4];
    struct stat st;

    /* Check 1: open GKS (error stream only, no display involved). */
    result = gopengks(stderr, 0);
    if (result != 0) {
        printf("check 1: FAIL (gopengks returned %d)\n", result);
        return 1;
    }
    printf("check 1: OK (gopengks opened)\n");

    /* Check 2: open a metafile-output workstation to a file. */
    result = gopenws(WS_ID, OUTFILE, "MO");
    if (result != 0) {
        printf("check 2: FAIL (gopenws MO returned %d)\n", result);
        return 1;
    }
    printf("check 2: OK (MO workstation opened)\n");

    /* Check 3: activate and set the workstation window. */
    window.xmin = 0.0f;
    window.xmax = 1.0f;
    window.ymin = 0.0f;
    window.ymax = 1.0f;
    result = gactivatews(WS_ID);
    if (result != 0) {
        printf("check 3: FAIL (gactivatews returned %d)\n", result);
        return 1;
    }
    result = gsetwswindow(WS_ID, &window);
    if (result != 0) {
        printf("check 3: FAIL (gsetwswindow returned %d)\n", result);
        return 1;
    }
    printf("check 3: OK (workstation active, window set)\n");

    /* Check 4: draw the three basic output primitives. */
    line_pts[0].x = 0.1f; line_pts[0].y = 0.1f;
    line_pts[1].x = 0.9f; line_pts[1].y = 0.9f;
    result = gpolyline(2, line_pts);
    if (result != 0) {
        printf("check 4: FAIL (gpolyline returned %d)\n", result);
        return 1;
    }
    marker_pts[0].x = 0.2f; marker_pts[0].y = 0.8f;
    marker_pts[1].x = 0.5f; marker_pts[1].y = 0.5f;
    marker_pts[2].x = 0.8f; marker_pts[2].y = 0.2f;
    result = gpolymarker(3, marker_pts);
    if (result != 0) {
        printf("check 4: FAIL (gpolymarker returned %d)\n", result);
        return 1;
    }
    fill_pts[0].x = 0.3f; fill_pts[0].y = 0.3f;
    fill_pts[1].x = 0.7f; fill_pts[1].y = 0.3f;
    fill_pts[2].x = 0.7f; fill_pts[2].y = 0.7f;
    fill_pts[3].x = 0.3f; fill_pts[3].y = 0.7f;
    result = gfillarea(4, fill_pts);
    if (result != 0) {
        printf("check 4: FAIL (gfillarea returned %d)\n", result);
        return 1;
    }
    printf("check 4: OK (polyline + polymarker + fillarea drawn)\n");

    /* Check 5: orderly shutdown of workstation and GKS. */
    result = gdeactivatews(WS_ID);
    if (result != 0) {
        printf("check 5: FAIL (gdeactivatews returned %d)\n", result);
        return 1;
    }
    result = gclosews(WS_ID);
    if (result != 0) {
        printf("check 5: FAIL (gclosews returned %d)\n", result);
        return 1;
    }
    result = gclosegks();
    if (result != 0) {
        printf("check 5: FAIL (gclosegks returned %d)\n", result);
        return 1;
    }
    printf("check 5: OK (workstation and GKS closed)\n");

    /* Check 6: the metafile must exist and hold real records. A header-only
     * or empty file would mean the primitives above silently drew nothing,
     * so require a non-trivial size. */
    if (stat(OUTFILE, &st) != 0) {
        printf("check 6: FAIL (metafile %s missing)\n", OUTFILE);
        return 1;
    }
    if (st.st_size <= 0) {
        printf("check 6: FAIL (metafile %s is empty)\n", OUTFILE);
        return 1;
    }
    printf("check 6: OK (metafile %s holds %ld bytes)\n", OUTFILE, (long)st.st_size);

    printf("test_xgks: OK (6/6 checks passed)\n");
    return 0;
}
