#include <cascade.h>

int main() {
  cascade::Cascade cascade;
  return cascade.is_running() ? 1 : 0;
}
