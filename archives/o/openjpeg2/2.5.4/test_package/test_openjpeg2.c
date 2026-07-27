#include <stdio.h>
#include <string.h>

#include <openjpeg.h>

static int check(int condition, const char *message)
{
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", message);
        return 1;
    }
    return 0;
}

int main(void)
{
    int failures = 0;

    const char *version = opj_version();
    failures += check(version != NULL && strstr(version, "2.5.4") != NULL,
                      "opj_version reports 2.5.4");

    opj_cparameters_t parameters;
    opj_set_default_encoder_parameters(&parameters);
    failures += check(parameters.numresolution > 0 &&
                          parameters.cblockw_init > 0 &&
                          parameters.cblockh_init > 0,
                      "default encoder parameters initialize coding geometry");

    opj_image_cmptparm_t component;
    memset(&component, 0, sizeof(component));
    component.dx = 1;
    component.dy = 1;
    component.w = 2;
    component.h = 2;
    component.prec = 8;
    component.sgnd = 0;

    opj_image_t *image = opj_image_create(1, &component, OPJ_CLRSPC_GRAY);
    failures += check(image != NULL, "opj_image_create returns an image");
    failures += check(image != NULL && image->numcomps == 1,
                      "image has one component");
    failures += check(image != NULL && image->comps[0].w == 2 &&
                          image->comps[0].h == 2,
                      "component dimensions are preserved");

    opj_codec_t *codec = opj_create_compress(OPJ_CODEC_J2K);
    failures += check(codec != NULL, "opj_create_compress creates J2K codec");

    opj_destroy_codec(codec);
    opj_image_destroy(image);

    if (failures != 0) {
        return 1;
    }

    printf("openjpeg2 consumer checks passed\n");
    return 0;
}
