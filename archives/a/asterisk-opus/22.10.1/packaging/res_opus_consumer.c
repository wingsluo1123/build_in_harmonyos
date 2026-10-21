#include "asterisk.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "asterisk/module.h"
#include "asterisk/format.h"
#include "asterisk/format_cache.h"
#include "asterisk/astobj2.h"
#include "asterisk/strings.h"

static int load_module(void)
{
    const char *result_path = getenv("ASTERISK_OPUS_CONSUMER_RESULT");
    struct ast_format *parsed = NULL;
    struct ast_format *roundtrip = NULL;
    struct ast_str *sdp = ast_str_create(256);
    const char *expected[] = {
        "a=fmtp:111 ", "maxplaybackrate=16000", "maxaveragebitrate=24000",
        "stereo=1", "sprop-stereo=1", "useinbandfec=1", "usedtx=1"
    };
    FILE *result;
    size_t index;
    int passed = 0;

    if (!result_path || !sdp || !ast_format_opus) {
        goto done;
    }
    parsed = ast_format_parse_sdp_fmtp(ast_format_opus,
        "MAXPLAYBACKRATE=16000; maxaveragebitrate=24000; stereo=1; "
        "sprop-stereo=1; useinbandfec=1; usedtx=1");
    if (!parsed || !ast_format_get_attribute_data(parsed)
        || ast_format_get_channel_count(parsed) != 2) {
        goto done;
    }
    ast_format_generate_sdp_fmtp(parsed, 111, &sdp);
    for (index = 0; index < sizeof(expected) / sizeof(expected[0]); ++index) {
        if (!strstr(ast_str_buffer(sdp), expected[index])) {
            goto done;
        }
    }
    roundtrip = ast_format_parse_sdp_fmtp(ast_format_opus,
        ast_str_buffer(sdp) + strlen("a=fmtp:111 "));
    if (!roundtrip || ast_format_get_channel_count(roundtrip) != 2) {
        goto done;
    }
    ast_str_reset(sdp);
    ast_format_generate_sdp_fmtp(roundtrip, 111, &sdp);
    for (index = 0; index < sizeof(expected) / sizeof(expected[0]); ++index) {
        if (!strstr(ast_str_buffer(sdp), expected[index])) {
            goto done;
        }
    }
    passed = 1;
done:
    if (result_path && (result = fopen(result_path, "w"))) {
        fprintf(result, "%s: Opus SDP parse, generation and roundtrip\n",
            passed ? "PASS" : "FAIL");
        fclose(result);
    }
    ao2_cleanup(roundtrip);
    ao2_cleanup(parsed);
    ast_free(sdp);
    return passed ? AST_MODULE_LOAD_SUCCESS : AST_MODULE_LOAD_DECLINE;
}

static int unload_module(void)
{
    return 0;
}

AST_MODULE_INFO(ASTERISK_GPL_KEY, AST_MODFLAG_LOAD_ORDER, "Opus SDP consumer",
    .support_level = AST_MODULE_SUPPORT_CORE,
    .load = load_module,
    .unload = unload_module,
    .requires = "res_format_attr_opus",
    .load_pri = AST_MODPRI_DEFAULT
);
