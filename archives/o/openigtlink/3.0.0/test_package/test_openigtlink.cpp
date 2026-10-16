/*=========================================================================

  Consumer test for the OpenIGTLink 3.0.0 Conan package on
  OpenHarmony / HarmonyOS.

  This is the layer-2 test of docs/TEST_QUALITY_SPEC.md: it is built *outside*
  the library source tree and uses only the installed package (the exported
  CMake target OpenIGTLink::OpenIGTLink), so it fails whenever the package is
  incomplete - which is exactly how the missing-header defect of upstream
  v3.0 (headers collected only for MSVC/Xcode) was caught.

  Coverage
    1. protocol constants baked into the installed igtlConfigure.h
    2. C utility layer (Source/igtlutil): byte-order conversion and CRC
    3. C++ message layer: TRANSFORM serialise / deserialise round trip
    4. end-to-end client/server round trip over a loopback TCP socket
    5. HarmonyOS-only case (new for the OHOS port): the process really runs on
       HarmonyOS, has a usable task-private TMPDIR, and the serialised message
       survives a TMPDIR round trip - the way a HarmonyOS app hands samples
       over from the network thread to the consumer thread.

=========================================================================*/

#include <cstdio>
#include <cstdlib>
#include <cstring>

/* installed package headers - all public headers are flat in <prefix>/include */
#include "igtlConfigure.h"
#include "igtl_header.h"
#include "igtl_transform.h"
#include "igtl_util.h"
#include "igtlMath.h"
#include "igtlMessageHeader.h"
#include "igtlTransformMessage.h"
#include "igtlServerSocket.h"
#include "igtlClientSocket.h"

#ifdef __OHOS__
#  include <sys/utsname.h>
#  include <unistd.h>
#endif

static int g_assertions = 0;

#define CHECK(cond)                                                          \
  do {                                                                       \
    ++g_assertions;                                                          \
    if (!(cond)) {                                                           \
      std::fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond);    \
      std::fflush(stderr);                                                   \
      return 1;                                                              \
    }                                                                        \
  } while (0)

static int MatrixEqual(const igtl::Matrix4x4& a, const igtl::Matrix4x4& b)
{
  return std::memcmp(static_cast<const void*>(a),
                     static_cast<const void*>(b),
                     sizeof(igtl::Matrix4x4)) == 0;
}

int main(void)
{
  /* ------------------------------------------------------------------ *
   * 1. constants from the installed igtlConfigure.h / igtl_header.h    *
   * ------------------------------------------------------------------ */
  CHECK(OpenIGTLink_PROTOCOL_VERSION      == 3);
  CHECK(OpenIGTLink_PROTOCOL_VERSION_3    == 3);
  CHECK(OpenIGTLink_HEADER_VERSION        == 2);
  CHECK(IGTL_HEADER_VERSION_2             == 2);
  CHECK(IGTL_HEADER_SIZE                  == 58);
  CHECK(IGTL_TRANSFORM_SIZE               == 48);

  /* ------------------------------------------------------------------ *
   * 2. C utility layer (igtlutil)                                      *
   * ------------------------------------------------------------------ */
  igtl_float32 cube[12] = { 46.0531f,  19.4709f, 46.0531f,  1.0f,
                           -0.954892f, 0.196632f, -0.222525f, 0.0f,
                           -0.196632f, 0.142857f, 0.970014f, 0.0f };
  igtl_float32 reference[12];
  std::memcpy(reference, cube, sizeof(cube));

  const igtl_uint64 crcA = igtl_transform_get_crc(cube);
  const igtl_uint64 crcB = igtl_transform_get_crc(cube);
  CHECK(crcA == crcB);
  CHECK(crcA != 0);

  /* on a little-endian host one swap must change the bytes ... */
  igtl_transform_convert_byte_order(cube);
  CHECK(std::memcmp(cube, reference, sizeof(cube)) != 0);
  CHECK(igtl_transform_get_crc(cube) != crcA);
  /* ... and the CRC must be invariant under the two-way conversion pair */
  igtl_transform_convert_byte_order(cube);
  CHECK(std::memcmp(cube, reference, sizeof(cube)) == 0);
  CHECK(igtl_transform_get_crc(cube) == crcA);

  /* ------------------------------------------------------------------ *
   * 3. C++ message layer: TRANSFORM serialise / deserialise             *
   * ------------------------------------------------------------------ */
  igtl::Matrix4x4 sent = { {  0.0f,  0.0f,  0.0f,  0.0f },
                           {  0.0f,  0.0f,  0.0f,  0.0f },
                           {  0.0f,  0.0f,  0.0f,  0.0f },
                           {  0.0f,  0.0f,  0.0f,  0.0f } };
  igtl::IdentityMatrix(sent);
  sent[0][3] = 46.0531f;
  sent[1][3] = 19.4709f;
  sent[2][3] = 46.0531f;

  igtl::TransformMessage::Pointer outgoing = igtl::TransformMessage::New();
  outgoing->AllocatePack();
  outgoing->SetTimeStamp(0, 1234567892);
  outgoing->SetDeviceName("OHOSConsumer");
  outgoing->SetMatrix(sent);
  outgoing->Pack();

  CHECK(outgoing->GetPackSize() == IGTL_HEADER_SIZE + IGTL_TRANSFORM_SIZE);
  CHECK(outgoing->GetPackBodySize() == IGTL_TRANSFORM_SIZE);
  CHECK(std::strcmp(outgoing->GetDeviceType(), "TRANSFORM") == 0);

  /* the wire image is in network byte order: verify the serialised header
     through the library's own header decoder instead of reading it raw */
  igtl::MessageHeader::Pointer header = igtl::MessageHeader::New();
  header->InitPack();
  std::memcpy(header->GetPackPointer(), outgoing->GetPackPointer(), IGTL_HEADER_SIZE);
  header->Unpack();

  const igtl_header* wire =
      static_cast<const igtl_header*>(header->GetPackPointer());
  CHECK(wire->header_version == IGTL_HEADER_VERSION_1);
  CHECK(std::strcmp(wire->name, "TRANSFORM") == 0);
  CHECK(std::strcmp(wire->device_name, "OHOSConsumer") == 0);
  CHECK(wire->timestamp == 1234567892u);
  CHECK(wire->body_size == IGTL_TRANSFORM_SIZE);
  CHECK(header->GetDeviceType() != NULL);
  CHECK(std::strcmp(header->GetDeviceType(), "TRANSFORM") == 0);

  igtl::TransformMessage::Pointer incoming = igtl::TransformMessage::New();
  incoming->SetMessageHeader(header);
  incoming->AllocatePack();
  CHECK(incoming->GetPackBodySize() == outgoing->GetPackBodySize());
  std::memcpy(incoming->GetPackBodyPointer(),
              outgoing->GetPackBodyPointer(),
              static_cast<size_t>(incoming->GetPackBodySize()));
  incoming->Unpack();

  igtl::Matrix4x4 received = { {  1.0f,  1.0f,  1.0f,  1.0f },
                               {  2.0f,  2.0f,  2.0f,  2.0f },
                               {  3.0f,  3.0f,  3.0f,  3.0f },
                               {  4.0f,  4.0f,  4.0f,  4.0f } };
  incoming->GetMatrix(received);
  CHECK(MatrixEqual(sent, received));
  CHECK(received[0][3] == 46.0531f);
  CHECK(received[1][3] == 19.4709f);
  CHECK(received[2][3] == 46.0531f);

  /* ------------------------------------------------------------------ *
   * 4. end-to-end round trip over a loopback TCP socket                 *
   * ------------------------------------------------------------------ */
  igtl::ServerSocket::Pointer server = igtl::ServerSocket::New();
  CHECK(server->CreateServer(0) == 0);          /* 0 -> ephemeral port */
  const int port = server->GetServerPort();
  CHECK(port > 0 && port < 65536);

  igtl::ClientSocket::Pointer client = igtl::ClientSocket::New();
  CHECK(client->ConnectToServer("127.0.0.1", port) == 0);

  igtl::ClientSocket::Pointer connection = server->WaitForConnection(5000);
  CHECK(connection.IsNotNull());
  CHECK(connection->GetConnected());

  /* Socket::Send() returns 1 on success (0 on error), not a byte count */
  CHECK(client->Send(outgoing->GetPackPointer(), outgoing->GetPackSize()) == 1);

  igtl::MessageHeader::Pointer streamedHeader = igtl::MessageHeader::New();
  streamedHeader->InitPack();
  CHECK(connection->Receive(streamedHeader->GetPackPointer(), IGTL_HEADER_SIZE)
        == IGTL_HEADER_SIZE);
  streamedHeader->Unpack();
  const igtl_header* streamedWire =
      static_cast<const igtl_header*>(streamedHeader->GetPackPointer());
  CHECK(std::strcmp(streamedWire->device_name, "OHOSConsumer") == 0);
  CHECK(streamedWire->body_size == IGTL_TRANSFORM_SIZE);

  igtl::TransformMessage::Pointer streamedMessage = igtl::TransformMessage::New();
  streamedMessage->SetMessageHeader(streamedHeader);
  streamedMessage->AllocatePack();
  CHECK(connection->Receive(streamedMessage->GetPackBodyPointer(),
                            streamedMessage->GetPackBodySize())
        == streamedMessage->GetPackBodySize());
  streamedMessage->Unpack();
  igtl::Matrix4x4 streamed = { {  0.0f,  0.0f,  0.0f,  0.0f },
                               {  0.0f,  0.0f,  0.0f,  0.0f },
                               {  0.0f,  0.0f,  0.0f,  0.0f },
                               {  0.0f,  0.0f,  0.0f,  0.0f } };
  streamedMessage->GetMatrix(streamed);
  CHECK(MatrixEqual(sent, streamed));
  connection->CloseSocket();
  client->CloseSocket();
  server->CloseSocket();

  /* ------------------------------------------------------------------ *
   * 5. HarmonyOS-only consumer contract (case added by the OHOS port)   *
   * ------------------------------------------------------------------ */
#ifdef __OHOS__
  struct utsname system;
  CHECK(uname(&system) == 0);
  CHECK(std::strcmp(system.sysname, "HarmonyOS") == 0);

  const char* tmpdir = std::getenv("TMPDIR");
  CHECK(tmpdir != NULL);
  CHECK(tmpdir != NULL && tmpdir[0] == '/');

  char path[4096];
  CHECK(tmpdir != NULL &&
        std::snprintf(path, sizeof(path), "%s/openigtlink-XXXXXX", tmpdir)
          < static_cast<int>(sizeof(path)));
  const int fd = mkstemp(path);
  CHECK(fd >= 0);

  const int packSize = outgoing->GetPackSize();
  CHECK(write(fd, outgoing->GetPackPointer(), static_cast<size_t>(packSize))
        == static_cast<ssize_t>(packSize));

  unsigned char* readBack =
      static_cast<unsigned char*>(std::calloc(static_cast<size_t>(packSize), 1));
  CHECK(readBack != NULL);
  const ssize_t got = pread(fd, readBack, static_cast<size_t>(packSize), 0);
  CHECK(got == static_cast<ssize_t>(packSize));
  CHECK(std::memcmp(readBack, outgoing->GetPackPointer(),
                    static_cast<size_t>(packSize)) == 0);

  /* the bytes read back must still decode into the same transform */
  igtl::MessageHeader::Pointer fileHeader = igtl::MessageHeader::New();
  fileHeader->InitPack();
  std::memcpy(fileHeader->GetPackPointer(), readBack, IGTL_HEADER_SIZE);
  fileHeader->Unpack();
  igtl::TransformMessage::Pointer fileMessage = igtl::TransformMessage::New();
  fileMessage->SetMessageHeader(fileHeader);
  fileMessage->AllocatePack();
  std::memcpy(fileMessage->GetPackBodyPointer(),
              readBack + IGTL_HEADER_SIZE,
              static_cast<size_t>(fileMessage->GetPackBodySize()));
  fileMessage->Unpack();
  igtl::Matrix4x4 fromFile = { {  0.0f,  0.0f,  0.0f,  0.0f },
                               {  0.0f,  0.0f,  0.0f,  0.0f },
                               {  0.0f,  0.0f,  0.0f,  0.0f },
                               {  0.0f,  0.0f,  0.0f,  0.0f } };
  fileMessage->GetMatrix(fromFile);
  CHECK(MatrixEqual(sent, fromFile));

  std::free(readBack);
  CHECK(close(fd) == 0);
  CHECK(unlink(path) == 0);
#endif /* __OHOS__ */

  std::printf("CONSUMER_1_OF_1_PASS assertions=%d pack_size=%d loopback_port=%d "
              "protocol=%d header=%d\n",
              g_assertions, outgoing->GetPackSize(), port,
              (int) OpenIGTLink_PROTOCOL_VERSION,
              (int) OpenIGTLink_HEADER_VERSION);
  std::fflush(stdout);
  return 0;
}
