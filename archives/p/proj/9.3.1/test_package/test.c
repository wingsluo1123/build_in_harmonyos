/*
 * proj functional test — creates a coordinate transformation and verifies output.
 * Tests: proj_info, proj_context_create, proj_create_crs_to_crs,
 *        proj_normalize_for_visualization, proj_trans, proj_destroy, proj_context_destroy
 */
#include <proj.h>
#include <stdio.h>
#include <math.h>

int main(void)
{
    /* --- Get PROJ version info --- */
    PJ_INFO info = proj_info();
    printf("PROJ version: %d.%d.%d\n", info.major, info.minor, info.patch);
    if (info.major != 9) {
        printf("ERROR: unexpected major version %d\n", info.major);
        return 1;
    }
    printf("proj_info: OK (v%d.%d.%d)\n", info.major, info.minor, info.patch);

    /* --- Create a coordinate transformation: WGS84 -> Web Mercator --- */
    PJ_CONTEXT *ctx = proj_context_create();
    if (!ctx) {
        printf("ERROR: proj_context_create failed\n");
        return 1;
    }
    printf("proj_context_create: OK\n");

    PJ *pj = proj_create_crs_to_crs(ctx, "EPSG:4326", "EPSG:3857", NULL);
    if (!pj) {
        printf("ERROR: proj_create_crs_to_crs failed\n");
        proj_context_destroy(ctx);
        return 1;
    }
    printf("proj_create_crs_to_crs(EPSG:4326 -> EPSG:3857): OK\n");

    /* Normalize for visualization (handles axis ordering).
     * Ownership note: proj_normalize_for_visualization() may return the same
     * PJ* pointer when no axis reorder is needed; only destroy the original
     * when it differs from the normalized result. */
    PJ *pj_norm = proj_normalize_for_visualization(ctx, pj);
    if (!pj_norm) {
        printf("ERROR: proj_normalize_for_visualization failed\n");
        proj_destroy(pj);
        proj_context_destroy(ctx);
        return 1;
    }
    if (pj_norm != pj)
        proj_destroy(pj);
    printf("proj_normalize_for_visualization: OK\n");

    /* --- Transform origin (lat=0, lon=0) -> should be (0, 0) --- */
    PJ_COORD c;
    c.lp.lam = 0.0;  /* longitude */
    c.lp.phi = 0.0;  /* latitude */
    PJ_COORD result = proj_trans(pj_norm, PJ_FWD, c);
    printf("proj_trans(0,0) -> (%.4f, %.4f)\n", result.xy.x, result.xy.y);

    /* Web Mercator origin maps to (0, 0) */
    if (fabs(result.xy.x) < 1e-9 && fabs(result.xy.y) < 1e-9) {
        printf("VERIFY: origin transform correct\n");
        printf("\n=== PROJ FUNCTIONAL TEST: PASSED ===\n");
    } else {
        printf("VERIFY: origin transform incorrect\n");
        printf("\n=== PROJ FUNCTIONAL TEST: FAILED ===\n");
        proj_destroy(pj_norm);
        proj_context_destroy(ctx);
        return 1;
    }

    proj_destroy(pj_norm);
    proj_context_destroy(ctx);
    return 0;
}
