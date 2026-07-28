/* test_package/test_libcurl.c — libcurl 8.5.0 L1 smoke test.
 * Initialize curl, get version info, verify basic API works. */
#include <stdio.h>
#include <string.h>
#include <curl/curl.h>

int main(void) {
    CURLcode ginit_rc = curl_global_init(CURL_GLOBAL_ALL);
    if (ginit_rc != CURLE_OK) {
        fprintf(stderr, "curl_global_init failed: %s\n", curl_easy_strerror(ginit_rc));
        return 1;
    }

    CURL *handle = curl_easy_init();
    if (!handle) {
        fprintf(stderr, "curl_easy_init failed\n");
        curl_global_cleanup();
        return 1;
    }

    char *curl_ver = curl_version();
    if (!curl_ver || strlen(curl_ver) == 0) {
        fprintf(stderr, "curl_version returned empty\n");
        curl_easy_cleanup(handle);
        curl_global_cleanup();
        return 1;
    }

    /* Set a URL without actually performing the transfer */
    CURLcode rc = curl_easy_setopt(handle, CURLOPT_URL, "https://example.com");
    if (rc != CURLE_OK) {
        fprintf(stderr, "curl_easy_setopt URL failed: %s\n", curl_easy_strerror(rc));
        curl_easy_cleanup(handle);
        curl_global_cleanup();
        return 1;
    }

    /* Verify the URL was set */
    char *effective_url = NULL;
    rc = curl_easy_getinfo(handle, CURLINFO_EFFECTIVE_URL, &effective_url);
    if (rc != CURLE_OK || !effective_url) {
        fprintf(stderr, "curl_easy_getinfo URL failed\n");
        curl_easy_cleanup(handle);
        curl_global_cleanup();
        return 1;
    }

    if (strcmp(effective_url, "https://example.com") != 0) {
        fprintf(stderr, "URL mismatch: %s\n", effective_url);
        curl_easy_cleanup(handle);
        curl_global_cleanup();
        return 1;
    }

    printf("libcurl 8.5.0: init/setopt/getinfo OK, version: %s\n", curl_ver);

    curl_easy_cleanup(handle);
    curl_global_cleanup();
    return 0;
}
