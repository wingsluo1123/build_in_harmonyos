#include <stdio.h>

#include <ldacBT.h>
#include <ldacBT_abr.h>

int main(void) {
    HANDLE_LDAC_BT encoder = ldacBT_get_handle();
    HANDLE_LDAC_ABR abr = ldac_ABR_get_handle();
    const int version = ldacBT_get_version();

    if (encoder == NULL || abr == NULL || version <= 0) {
        fprintf(stderr, "Failed to allocate LDAC handles or read the version\n");
        return 1;
    }

    if (ldacBT_init_handle_encode(encoder, 679, LDACBT_EQMID_SQ,
                                  LDACBT_CHANNEL_MODE_STEREO,
                                  LDACBT_SMPL_FMT_S16, 48000) != 0) {
        fprintf(stderr, "Failed to initialize the LDAC encoder\n");
        return 2;
    }

    if (ldacBT_get_sampling_freq(encoder) != 48000 ||
        ldacBT_get_eqmid(encoder) != LDACBT_EQMID_SQ ||
        ldac_ABR_Init(abr, 100) != 0) {
        fprintf(stderr, "LDAC encoder or ABR state validation failed\n");
        return 3;
    }

    printf("libldac: version=0x%06x sample_rate=%d eqmid=%d\n",
           version, ldacBT_get_sampling_freq(encoder), ldacBT_get_eqmid(encoder));
    ldac_ABR_free_handle(abr);
    ldacBT_close_handle(encoder);
    ldacBT_free_handle(encoder);
    return 0;
}
