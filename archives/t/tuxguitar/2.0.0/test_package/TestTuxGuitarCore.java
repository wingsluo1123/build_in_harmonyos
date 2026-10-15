import app.tuxguitar.song.factory.TGFactory;
import app.tuxguitar.song.managers.TGSongManager;
import app.tuxguitar.song.models.TGBeat;
import app.tuxguitar.song.models.TGDuration;
import app.tuxguitar.song.models.TGMeasure;
import app.tuxguitar.song.models.TGNote;
import app.tuxguitar.song.models.TGSong;
import app.tuxguitar.song.models.TGTrack;
import app.tuxguitar.song.models.TGVoice;
import app.tuxguitar.util.TGMusicKeyUtils;
import app.tuxguitar.util.TGVersion;

/**
 * Consumer test — exercises the packaged TuxGuitar core JARs through their public API.
 * Tested package: tuxguitar/2.0.0 (libexec/tuxguitar-lib-*.jar + runtime deps).
 */
public class TestTuxGuitarCore {

    private static int passed = 0;
    private static int failed = 0;

    private static void check(String name, boolean ok, String detail) {
        if (ok) {
            passed++;
            System.out.println("TEST PASS  " + name + (detail.isEmpty() ? "" : "  (" + detail + ")"));
        } else {
            failed++;
            System.out.println("TEST FAIL  " + name + (detail.isEmpty() ? "" : "  (" + detail + ")"));
        }
    }

    public static void main(String[] args) {
        System.out.println("== TuxGuitar core consumer test ==");
        System.out.println("loaded app.tuxguitar.util.TGVersion from: "
                + TGVersion.class.getProtectionDomain().getCodeSource().getLocation());

        // 1) version parsing through the public API
        TGVersion v = new TGVersion("2.0.0");
        check("version.parse", v.getMajor() == 2 && v.getMinor() == 0 && v.getRevision() == 0,
                v.getMajor() + "." + v.getMinor() + "." + v.getRevision());

        // 2) the packaged JAR really is 2.0.0
        check("version.packageIs2_0_0",
                TGVersion.CURRENT.isSameVersion(new TGVersion(2, 0, 0))
                        && TGVersion.CURRENT.toString().startsWith("2.0"),
                "CURRENT=" + TGVersion.CURRENT);

        // 3) version ordering contract
        check("version.ordering", new TGVersion("2.1.0").compareTo(new TGVersion("2.0.0")) > 0
                        && new TGVersion("2.0.0").compareTo(new TGVersion("2.0.0")) == 0,
                "2.1.0 > 2.0.0");

        // 4) song construction via TGSongManager
        TGSongManager songMgr = new TGSongManager();
        TGSong song = songMgr.newSong();
        check("song.defaultStructure",
                song != null && song.countTracks() == 1 && song.countMeasureHeaders() == 1
                        && song.getTrack(0).countMeasures() == 1,
                "tracks=" + (song == null ? -1 : song.countTracks())
                        + " headers=" + (song == null ? -1 : song.countMeasureHeaders()));

        // 5) default guitar tuning has 6 strings
        TGTrack track = song.getTrack(0);
        check("song.defaultTrackStrings", track.getStrings().size() == 6,
                "strings=" + track.getStrings().size());

        // 6) add a note through the measure manager and read it back
        TGFactory factory = songMgr.getFactory();
        TGMeasure measure = track.getMeasure(0);
        TGBeat beat = factory.newBeat();
        beat.setPreciseStart(0L);
        measure.addBeat(beat);
        TGDuration duration = factory.newDuration();
        duration.setValue(TGDuration.QUARTER);
        TGNote note = factory.newNote();
        note.setValue(5);
        note.setString(1);
        songMgr.getMeasureManager().addNote(beat, note, duration, 0);
        TGVoice voice = beat.getVoice(0);
        check("song.addNote", voice.countNotes() == 1 && voice.getNote(0).getValue() == 5
                        && voice.getNote(0).getString() == 1,
                "notes=" + voice.countNotes());

        // 7) music-theory helper (pure Java, no platform dependency)
        check("musicKey.noteNameOctave",
                "A".equals(TGMusicKeyUtils.noteName(69, TGMusicKeyUtils.NATURAL))
                        && TGMusicKeyUtils.noteOctave(69) == 4,
                "midi69 -> A4");

        System.out.println("CORE TEST SUMMARY: passed=" + passed + " failed=" + failed);
        if (failed > 0) {
            System.exit(1);
        }
    }
}
