#include <geos_c.h>

#include <math.h>
#include <stdio.h>
#include <string.h>


int main(void)
{
    GEOSContextHandle_t context = GEOS_init_r();
    GEOSWKTReader *reader = NULL;
    GEOSGeometry *origin = NULL;
    GEOSGeometry *point = NULL;
    GEOSGeometry *polygon = NULL;
    double distance = 0.0;
    int contains = 0;
    int result = 1;

    if (context == NULL || strstr(GEOSversion(), "3.12.1") == NULL) {
        fprintf(stderr, "unexpected GEOS version: %s\n", GEOSversion());
        goto cleanup;
    }

    reader = GEOSWKTReader_create_r(context);
    if (reader == NULL) {
        fprintf(stderr, "failed to create WKT reader\n");
        goto cleanup;
    }

    origin = GEOSWKTReader_read_r(context, reader, "POINT (0 0)");
    point = GEOSWKTReader_read_r(context, reader, "POINT (3 4)");
    polygon = GEOSWKTReader_read_r(
        context, reader, "POLYGON ((0 0, 10 0, 10 10, 0 10, 0 0))");
    if (origin == NULL || point == NULL || polygon == NULL) {
        fprintf(stderr, "failed to parse test geometries\n");
        goto cleanup;
    }

    if (GEOSDistance_r(context, origin, point, &distance) != 1 ||
        fabs(distance - 5.0) > 1e-12) {
        fprintf(stderr, "unexpected distance: %.17g\n", distance);
        goto cleanup;
    }

    contains = GEOSContains_r(context, polygon, point);
    if (contains != 1) {
        fprintf(stderr, "polygon containment failed: %d\n", contains);
        goto cleanup;
    }

    printf("GEOS %s: distance and containment checks passed\n", GEOSversion());
    result = 0;

cleanup:
    if (context != NULL) {
        if (polygon != NULL) {
            GEOSGeom_destroy_r(context, polygon);
        }
        if (point != NULL) {
            GEOSGeom_destroy_r(context, point);
        }
        if (origin != NULL) {
            GEOSGeom_destroy_r(context, origin);
        }
        if (reader != NULL) {
            GEOSWKTReader_destroy_r(context, reader);
        }
        GEOS_finish_r(context);
    }
    return result;
}
