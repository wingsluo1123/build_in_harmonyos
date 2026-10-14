#include <snappy.h>
#include <snappy-c.h>
#include <algorithm>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iterator>
#include <string>
#include <vector>
#include <unistd.h>

#define CHECK(expr) do { if (!(expr)) { std::fprintf(stderr, "FAIL line %d: %s\n", __LINE__, #expr); std::exit(1); } } while (0)

int main() {
    std::string plain;
    for (size_t i=0;i<100000;++i) plain.push_back(static_cast<char>((i*37+i/64)%256));
    plain += "HarmonyOS \xe4\xba\x91\xe6\x9c\xb5";
    std::string compressed, restored;
    const size_t compressed_size=snappy::Compress(plain.data(), plain.size(), &compressed);
    CHECK(compressed_size==compressed.size());
    CHECK(snappy::IsValidCompressedBuffer(compressed.data(), compressed.size()));
    size_t expected=0;
    CHECK(snappy::GetUncompressedLength(compressed.data(), compressed.size(), &expected) && expected==plain.size());
    CHECK(snappy::Uncompress(compressed.data(), compressed.size(), &restored) && restored==plain);
    const char invalid[]={static_cast<char>(0x80)};
    CHECK(!snappy::IsValidCompressedBuffer(invalid, sizeof invalid));
    CHECK(!snappy::GetUncompressedLength(invalid, sizeof invalid, &expected));
    std::vector<char> buffer(snappy_max_compressed_length(plain.size()));
    size_t length=buffer.size();
    CHECK(snappy_compress(plain.data(), plain.size(), buffer.data(), &length)==SNAPPY_OK);
    CHECK(snappy_validate_compressed_buffer(buffer.data(), length)==SNAPPY_OK);
    size_t decoded_length=plain.size()-1;
    std::vector<char> decoded(plain.size());
    CHECK(snappy_uncompress(buffer.data(), length, decoded.data(), &decoded_length)==SNAPPY_BUFFER_TOO_SMALL);
    decoded_length=decoded.size();
    CHECK(snappy_uncompress(buffer.data(), length, decoded.data(), &decoded_length)==SNAPPY_OK);
    CHECK(decoded_length==plain.size() && std::equal(decoded.begin(), decoded.end(), plain.begin()));
    std::string empty;
    CHECK(snappy::Compress("",0,&compressed)>0 && snappy::Uncompress(compressed.data(),compressed.size(),&empty) && empty.empty());
#ifdef __OHOS__
    CHECK(sizeof(void*)==8);
    const char* tmp=std::getenv("TMPDIR");
    CHECK(tmp && tmp[0]=='/' && std::string(tmp).rfind("/tmp/",0)!=0);
    const std::string path=std::string(tmp)+"/snappy-"+std::to_string(getpid())+".bin";
    { std::ofstream file(path,std::ios::binary); file.write(buffer.data(),length); CHECK(file.good()); }
    std::ifstream file(path,std::ios::binary);
    CHECK(file.good());
    const std::string disk{std::istreambuf_iterator<char>(file),std::istreambuf_iterator<char>()};
    CHECK(disk.size()==length && std::equal(disk.begin(),disk.end(),buffer.begin()));
    CHECK(snappy::Uncompress(disk.data(),disk.size(),&restored) && restored==plain);
    file.close();
    CHECK(unlink(path.c_str())==0);
    std::puts("OHOS_COMPRESSED_PRIVATE_FILE_CPP_DECODE_PASS");
#endif
    std::puts("SNAPPY_C_CPP_CORRUPT_CAPACITY_EMPTY_ROUNDTRIP_PASS");
}
