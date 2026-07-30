#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "gdal.h"
#include "gdal_version.h"
#include "cpl_conv.h"
#include "ogr_srs_api.h"

static void require_true(int condition, const char *message)
{
    if (!condition) {
        fprintf(stderr, "GDAL test failed: %s\n", message);
        exit(1);
    }
}

int main(void)
{
    GDALAllRegister();

    const char *release_name = GDALVersionInfo("RELEASE_NAME");
    require_true(release_name != NULL, "release name is available");
    require_true(strcmp(release_name, "3.9.2") == 0, "release version is 3.9.2");
    require_true(GDALGetDriverCount() > 0, "at least one raster driver is registered");

    GDALDriverH mem_driver = GDALGetDriverByName("MEM");
    require_true(mem_driver != NULL, "MEM raster driver is registered");

    GDALDatasetH dataset = GDALCreate(mem_driver, "", 2, 2, 1, GDT_Byte, NULL);
    require_true(dataset != NULL, "MEM dataset can be created");
    require_true(GDALGetRasterXSize(dataset) == 2, "dataset width is preserved");
    require_true(GDALGetRasterYSize(dataset) == 2, "dataset height is preserved");

    OGRSpatialReferenceH srs = OSRNewSpatialReference(NULL);
    require_true(srs != NULL, "spatial reference can be allocated");
    require_true(OSRSetWellKnownGeogCS(srs, "WGS84") == OGRERR_NONE, "WGS84 spatial reference can be set");
    char *wkt = NULL;
    require_true(OSRExportToWkt(srs, &wkt) == OGRERR_NONE, "spatial reference exports to WKT");
    require_true(wkt != NULL && strstr(wkt, "WGS 84") != NULL, "exported WKT names WGS 84");

    CPLFree(wkt);
    OSRDestroySpatialReference(srs);
    GDALClose(dataset);
    GDALDestroyDriverManager();
    return 0;
}
