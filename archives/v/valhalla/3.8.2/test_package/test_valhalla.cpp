// Consumer test for the valhalla package.
//
// Exercises public headers that only depend on the installed valhalla
// headers (GraphId, PointLL) and links against the shipped libvalhalla, so
// it validates both the include layout and the shared/static library link.

#include <valhalla/baldr/graphid.h>
#include <valhalla/midgard/pointll.h>

#include <cassert>
#include <cstdio>

using valhalla::baldr::GraphId;
using valhalla::midgard::PointLL;

int main() {
  // ---- GraphId: pack/unpack of tile id, hierarchy level and local id -------
  GraphId id(1234u, 2u, 42u);
  assert(id.is_valid());
  assert(id.tileid() == 1234u);   // assertion 1
  assert(id.level() == 2u);       // assertion 2
  assert(id.id() == 42u);         // assertion 3

  GraphId other(1234u, 2u, 43u);
  assert(id != other);            // assertion 4
  assert(id < other);             // assertion 5

  GraphId invalid;
  assert(!invalid.is_valid());    // assertion 6

  GraphId incremented = id;
  incremented++;
  assert(incremented.id() == 43u); // assertion 7

  // ---- PointLL: great-circle distance (spherical geometry) -----------------
  PointLL sf(-122.4194, 37.7749);
  PointLL nyc(-73.9857, 40.7484);
  const double d = sf.Distance(nyc);

  assert(d > 4100000.0 && d < 4160000.0); // assertion 8: ~4130 km
  assert(sf.Distance(sf) < 0.001);        // assertion 9

  std::printf("valhalla consumer OK: graphid=%llu distance=%.1f m\n",
              static_cast<unsigned long long>(id.value), d);
  return 0;
}
