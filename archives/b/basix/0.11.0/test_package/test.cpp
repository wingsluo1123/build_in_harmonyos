#include <basix/finite-element.h>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>
#include <sys/stat.h>
#include <sys/utsname.h>
#include <unistd.h>

int main(int argc, char **argv)
{
  auto element0 = basix::create_element<float>(
      basix::element::family::P, basix::cell::type::triangle, 1,
      basix::element::lagrange_variant::equispaced,
      basix::element::dpc_variant::unset, false);
  auto element1 = basix::create_element<double>(
      basix::element::family::P, basix::cell::type::triangle, 1,
      basix::element::lagrange_variant::equispaced,
      basix::element::dpc_variant::unset, false);
  if (element0.dim() != 3 || element1.dim() != 3)
    return 1;
  if (argc == 1)
  {
    std::puts("BASIX_CONSUMER_FLOAT_DOUBLE=2/2 PASS");
    return 0;
  }
  if (argc != 2 || std::strcmp(argv[1], "--harmony") != 0)
    return 2;
  utsname os{};
  if (uname(&os) != 0 || std::strcmp(os.sysname, "HarmonyOS") != 0)
    return 3;
  const char *tmp = std::getenv("TMPDIR");
  if (!tmp || !*tmp)
    return 4;
  std::string name = std::string(tmp) + "/basix-computed-state-XXXXXX";
  std::vector<char> path(name.begin(), name.end());
  path.push_back('\0');
  int fd = mkstemp(path.data());
  if (fd < 0)
    return 5;
  struct stat st{};
  bool owner_ok = fstat(fd, &st) == 0 && st.st_uid == getuid();
  bool removed = unlink(path.data()) == 0;
  std::uint64_t actual = element0.dim() + element1.dim();
  std::uint64_t readback = 0;
  bool roundtrip = write(fd, &actual, sizeof(actual)) == sizeof(actual)
      && lseek(fd, 0, SEEK_SET) == 0
      && read(fd, &readback, sizeof(readback)) == sizeof(readback)
      && actual == readback && readback == 6;
  int rc = close(fd);
  if (!owner_ok || !removed || !roundtrip || rc != 0)
    return 6;
  std::puts("HARMONY_BASIX_COMPUTED_STATE_POSIX_OWNER=1/1 PASS");
  return 0;
}
