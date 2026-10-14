// id3lib test_package — real API round-trip (R34/R53):
// create tag -> write file -> re-open -> assert fields -> modify -> re-read.
#include <id3/tag.h>
#include <id3/misc_support.h>

#include <cstdio>
#include <cstring>
#include <string>

static int g_fail = 0;
static int g_pass = 0;

#define CHECK(cond, label) do {                                        \
  if (cond) { ++g_pass; std::printf("PASS: %s\n", label); }            \
  else { ++g_fail; std::fprintf(stderr, "FAIL: %s\n", label); }        \
} while (0)

static std::string GetTextOf(const ID3_Frame* frame)
{
  if (frame == nullptr)
  {
    return std::string();
  }
  char* text = ID3_GetString(frame, ID3FN_TEXT);
  std::string result(text ? text : "");
  delete[] text;
  return result;
}

int main()
{
  const char* kFile = "id3lib_roundtrip.mp3";
  std::remove(kFile);
  {
    std::FILE* f = std::fopen(kFile, "wb");
    if (f == nullptr)
    {
      std::fprintf(stderr, "FAIL: cannot create %s\n", kFile);
      return 2;
    }
    const unsigned char mp3[] = {0xFF, 0xFB, 0x90, 0x00};
    std::fwrite(mp3, 1, sizeof(mp3), f);
    std::fclose(f);
  }

  /* 1) create a tag and write it */
  {
    ID3_Tag tag;
    tag.Link(kFile);
    ID3_Frame artist(ID3FID_LEADARTIST);
    artist.GetField(ID3FN_TEXT)->Set("HarmonyOS Artist");
    tag.AddFrame(artist);
    ID3_Frame title(ID3FID_TITLE);
    title.GetField(ID3FN_TEXT)->Set("PC Migrated Song");
    tag.AddFrame(title);
    tag.SetPadding(false);
    tag.Update(ID3TT_ID3V2);
  }

  /* 2) re-open with a fresh tag object and assert the fields */
  {
    ID3_Tag tag;
    tag.Link(kFile);
    CHECK(tag.Size() > 0, "tag has content after Update()");
    const ID3_Frame* a = tag.Find(ID3FID_LEADARTIST);
    CHECK(a != nullptr, "artist frame found after re-read");
    CHECK(GetTextOf(a) == "HarmonyOS Artist", "artist text round-trips");
    const ID3_Frame* t = tag.Find(ID3FID_TITLE);
    CHECK(t != nullptr, "title frame found after re-read");
    CHECK(GetTextOf(t) == "PC Migrated Song", "title text round-trips");
  }

  /* 3) modify and update again */
  {
    ID3_Tag tag;
    tag.Link(kFile);
    ID3_Frame album(ID3FID_ALBUM);
    album.GetField(ID3FN_TEXT)->Set("Migration Album");
    tag.AddFrame(album);
    tag.Update(ID3TT_ID3V2);
  }
  {
    ID3_Tag tag;
    tag.Link(kFile);
    CHECK(GetTextOf(tag.Find(ID3FID_ALBUM)) == "Migration Album",
          "album persists after second update");
    CHECK(GetTextOf(tag.Find(ID3FID_LEADARTIST)) == "HarmonyOS Artist",
          "artist survives second update");
  }

  std::remove(kFile);
  std::printf("RESULT: %d passed, %d failed\n", g_pass, g_fail);
  return g_fail == 0 ? 0 : 1;
}
