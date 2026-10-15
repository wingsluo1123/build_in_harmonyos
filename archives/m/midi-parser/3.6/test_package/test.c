/*
 * test_package for midi-parser 3.6 — Conan L1 smoke test.
 *
 * Actually parses an in-memory minimal SMF (format 0, one track with
 * Note On / Note Off / End-of-Track) through the library state machine
 * and asserts the observed events.  This is a real consumer-side test
 * of the packaged library, not a print-only stub (R34).
 */
#include <stdio.h>
#include <stdint.h>
#include <string.h>

#include "midi-parser.h"

static const uint8_t smf[] = {
    'M', 'T', 'h', 'd', 0x00, 0x00, 0x00, 0x06, /* header chunk */
    0x00, 0x00,                                 /* format 0 */
    0x00, 0x01,                                 /* 1 track */
    0x00, 0x78,                                 /* 120 ppq */
    'M', 'T', 'r', 'k', 0x00, 0x00, 0x00, 0x0c, /* track chunk, len 12 */
    0x00, 0x90, 0x3c, 0x64,                     /* t=0 Note On  C4 vel 100 */
    0x60, 0x80, 0x3c, 0x00,                     /* t=96 Note Off C4 */
    0x00, 0xff, 0x2f, 0x00                      /* End of Track */
};

int main(void)
{
    struct midi_parser parser;
    int saw_header = 0, saw_track = 0, saw_note_on = 0, saw_note_off = 0, saw_eot = 0, saw_eob = 0;

    memset(&parser, 0, sizeof(parser));
    parser.in = smf;
    parser.size = (int32_t)sizeof(smf);

    while (1) {
        int rc = midi_parse(&parser);
        if (rc == MIDI_PARSER_EOB) {
            saw_eob = 1;
            break;
        }
        if (rc == MIDI_PARSER_ERROR) {
            fprintf(stderr, "midi_parse error at state=%d\n", parser.state);
            return 1;
        }
        switch (rc) {
        case MIDI_PARSER_HEADER:
            if (parser.header.format != 0 || parser.header.tracks_count != 1
                || parser.header.time_division != 120)
                return 2;
            saw_header = 1;
            break;
        case MIDI_PARSER_TRACK:
            if (parser.track.size != 12)
                return 3;
            saw_track = 1;
            break;
        case MIDI_PARSER_TRACK_MIDI:
            if (parser.midi.status == 0x9 && parser.midi.param1 == 0x3c)
                saw_note_on = 1;
            else if (parser.midi.status == 0x8 && parser.midi.param1 == 0x3c)
                saw_note_off = 1;
            break;
        case MIDI_PARSER_TRACK_META:
            if (parser.meta.type == MIDI_META_END_OF_TRACK)
                saw_eot = 1;
            break;
        default:
            break;
        }
    }

    if (!saw_header || !saw_track || !saw_note_on || !saw_note_off || !saw_eot || !saw_eob) {
        fprintf(stderr, "missing events: header=%d track=%d note_on=%d note_off=%d eot=%d eob=%d\n",
                saw_header, saw_track, saw_note_on, saw_note_off, saw_eot, saw_eob);
        return 4;
    }

    printf("midi-parser 3.6 test_package: OK (header/track/note-on/note-off/EOT/EOB all observed)\n");
    return 0;
}
