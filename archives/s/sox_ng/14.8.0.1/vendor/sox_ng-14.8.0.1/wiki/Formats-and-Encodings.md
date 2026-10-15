# Formats and Encodings

`ffmpeg` has the concepts of format containers and stream formats.

More or less, that corresponds to what SoX means by audio file formats
and encodings.

For example, a `.wav` file can contain 16-bit signed integer PCM samples
with two channels at 44100 samples per second; the encoding is 16s and
the number of channels and sample rate are held elsewhere.

SoX handles a lot of formats and a lot of encodings. For example,
a `.wav` file can contain MPEG-1 level 3 data (MP3) and
A-law compressed format can be found in `.au`, `.aifc`, `.raw`, `.gsrt`,
`.maud`, `.voc`, `.wav`, `.wve`, Psion Record and Sphere file formats.

A file format, in SoX-think, is a filename extension, though it can
also be deduced from the file contents if it has certain fixed bytes
as fixed offsets. To read and write to such a file, it has a format handler
which may be able read more than one filename extension. For example,
`.aif` and `.aiff` files are the same thing.

Once a SoX format handler has been selected, it has to handle
all the various encodings that might be contained in that format
and there are subsections of shared code to handle, for example, A-law
in all the formats that can contain it.

The file formats SoX currently knows are listed in `formats.h`
(the various possible filename extensions are listed in each handler)
and the encodings in `sox_ng.h`:

    typedef enum sox_encoding_t {
      SOX_ENCODING_UNKNOWN   , /**< encoding has not yet been determined */

      SOX_ENCODING_SIGN2     , /**< signed linear 2's comp: Mac */
      SOX_ENCODING_UNSIGNED  , /**< unsigned linear: Sound Blaster */
      SOX_ENCODING_FLOAT     , /**< floating point (binary format) */
      SOX_ENCODING_FLOAT_TEXT, /**< floating point (text format) */
      SOX_ENCODING_FLAC      , /**< FLAC compression */
      SOX_ENCODING_HCOM      , /**< Mac FSSD files with Huffman compression */
      SOX_ENCODING_WAVPACK   , /**< WavPack with integer samples */
      SOX_ENCODING_WAVPACKF  , /**< WavPack with float samples */
      SOX_ENCODING_ULAW      , /**< u-law signed logs: US telephony, SPARC */
      SOX_ENCODING_ALAW      , /**< A-law signed logs: non-US telephony, Psion */
      SOX_ENCODING_G721      , /**< G.721 4-bit ADPCM */
      SOX_ENCODING_G723      , /**< G.723 3 or 5 bit ADPCM */
      SOX_ENCODING_CL_ADPCM  , /**< Creative Labs 8 --> 2,3,4 bit Compressed PCM */
      SOX_ENCODING_CL_ADPCM16, /**< Creative Labs 16 --> 4 bit Compressed PCM */
      SOX_ENCODING_MS_ADPCM  , /**< Microsoft Compressed PCM */
      SOX_ENCODING_IMA_ADPCM , /**< IMA Compressed PCM */
      SOX_ENCODING_OKI_ADPCM , /**< Dialogic/OKI Compressed PCM */
      SOX_ENCODING_DPCM      , /**< Differential PCM: Fasttracker 2 (xi) */
      SOX_ENCODING_DWVW      , /**< Delta Width Variable Word */
      SOX_ENCODING_DWVWN     , /**< Delta Width Variable Word N-bit */
      SOX_ENCODING_GSM       , /**< GSM 6.10 33byte frame lossy compression */
      SOX_ENCODING_MP1       , /**< MPEG 1 Layer 1 compression */
      SOX_ENCODING_MP2       , /**< MPEG 1 Layer 2 compression */
      SOX_ENCODING_MP3       , /**< MPEG 1 Layer 3 compression */
      SOX_ENCODING_VORBIS    , /**< Vorbis compression */
      SOX_ENCODING_AMR_WB    , /**< AMR-WB compression */
      SOX_ENCODING_AMR_NB    , /**< AMR-NB compression */
      SOX_ENCODING_CVSD      , /**< Continuously Variable Slope Delta modulation */
      SOX_ENCODING_LPC10     , /**< Linear Predictive Coding */
      SOX_ENCODING_OPUS      , /**< Opus compression */
      SOX_ENCODING_DSD       , /**< Direct Stream Digital */

      SOX_ENCODINGS            /**< End of list marker */
    } sox_encoding_t;

which must match the entries in `formats.c:s_sox_encodings_info[]`
which has their attributes and names.
