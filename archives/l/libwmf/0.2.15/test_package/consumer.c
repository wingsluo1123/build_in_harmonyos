#include <libwmf/api.h>
#include <libwmf/svg.h>
#include <stdio.h>

int main(void)
{
    wmfAPI *api = NULL;
    wmfAPI_Options options = {0};
    options.function = wmf_svg_function;
    if (wmf_api_create(&api, WMF_OPT_FUNCTION, &options) != wmf_E_None || api == NULL)
        return 1;
    if (wmf_api_destroy(api) != wmf_E_None)
        return 2;
    puts("LIBWMF_CONSUMER_1_OF_1_PASS");
    return 0;
}
