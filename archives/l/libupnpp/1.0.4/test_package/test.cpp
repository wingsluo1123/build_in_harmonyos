#include <libupnpp/base64.hxx>
#include <libupnpp/upnpavutils.hxx>
#include <iostream>
#include <string>

static int failures = 0;
static void check(bool result, const char* label)
{
    std::cout << (result ? "PASS " : "FAIL ") << label << '\n';
    if (!result) ++failures;
}

int main()
{
    std::string decoded;
    check(UPnPP::base64_encode("").empty() &&
          UPnPP::base64_decode("", decoded) && decoded.empty(), "empty base64");
    check(UPnPP::base64_encode("hello") == "aGVsbG8=" &&
          UPnPP::base64_decode("aGVsbG8=", decoded) && decoded == "hello", "known base64");
    const char bytes[] = {0, char(255), 1, char(254)};
    const std::string binary(bytes, sizeof(bytes));
    check(UPnPP::base64_decode(UPnPP::base64_encode(binary), decoded) &&
          decoded == binary, "binary roundtrip");
    check(UPnPP::base64_encode("1") == "MQ==", "one byte padding");
    check(UPnPP::base64_encode("12") == "MTI=", "two byte padding");
    check(UPnPP::upnpduration(3723000) == "1:02:03" &&
          UPnPP::upnpdurationtos("1:02:03") == 3723, "duration roundtrip");
    UPnPP::ProtocolinfoEntry entry;
    check(UPnPP::parseProtoInfEntry("http-get:*:audio/mpeg:*", entry) &&
          entry.protocol == "http-get" && entry.network == "*" &&
          entry.contentFormat == "audio/mpeg", "protocol info");
    check(!UPnPP::parseProtoInfEntry("broken", entry), "malformed protocol info");
    if (failures) return 1;
    std::cout << "LIBUPNPP_CONSUMER_RESULT=8/8\n";
    return 0;
}
