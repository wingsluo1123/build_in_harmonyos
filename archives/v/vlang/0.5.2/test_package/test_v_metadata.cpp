#include <cstring>

int main() {
    const char *package_name = "vlang";
    return std::strcmp(package_name, "vlang") == 0 ? 0 : 1;
}
