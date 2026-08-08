from conan import ConanFile


class LibtorrentTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Verify the library can be linked
        import os
        test_cpp = os.path.join(self.source_folder, "test_package.cpp")
        with open(test_cpp, "w") as f:
            f.write("""
#include <torrent/torrent.h>
#include <torrent/exceptions.h>

int main() {
    // Link test: just reference a symbol from the library
    return torrent::is_initialized() ? 0 : 0;
}
""")
        self.run("clang++ -std=c++17 -o test_libtorrent test_package.cpp "
                 "-ltorrent -lcrypto -lz -lcurl -lpthread -ldl",
                 env="conanrun")
        self.run("./test_libtorrent", env="conanrun")
