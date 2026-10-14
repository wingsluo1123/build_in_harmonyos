#!/usr/bin/env python3
"""Consumer test: the installed tubeup package must expose a working API.

Exercises the real packaged surface: the docopt CLI parser, the TubeUp
download-option generation, archive.org metadata construction and the
identifier/file utilities. Run by test_package/conanfile.py via self.run.
"""
import os
import sys


def main(argv):
    if len(argv) > 1 and argv[1]:
        for entry in argv[1].split(os.pathsep):
            if entry and entry not in sys.path:
                sys.path.insert(0, entry)

    import docopt
    import internetarchive
    import tubeup
    from tubeup.TubeUp import TubeUp
    from tubeup.utils import sanitize_identifier, check_is_file_empty

    # installed version + declared Conan dependency are importable
    assert tubeup.__version__ == "2026.5.8", tubeup.__version__
    assert hasattr(internetarchive, "get_item")

    # docopt parses the real CLI docstring (upstream entry point contract)
    import tubeup.__main__ as cli
    args = docopt.docopt(
        cli.__doc__,
        argv=["-x", "socks5://localhost:9050",
              "https://example.com/watch?v=abc123"])
    assert args["--proxy"] == "socks5://localhost:9050"
    assert args["<url>"] == ["https://example.com/watch?v=abc123"]

    tu = TubeUp(verbose=True)
    assert tu.determine_collection_type("https://soundcloud.com/x") == "opensource_audio"
    assert tu.determine_collection_type(
        "https://www.youtube.com/watch?v=x") == "opensource_movies"
    assert TubeUp.determine_licenseurl(
        {"license": "Attribution"}) == "https://creativecommons.org/licenses/by/2.0/"

    # download option generation
    opts = tu.generate_ydl_options(
        lambda d: None, proxy_url="http://proxy.local:8080",
        use_download_archive=True)
    assert opts["restrictfilenames"] is True
    assert opts["writeinfojson"] is True
    assert opts["proxy"] == "http://proxy.local:8080"
    assert opts["outtmpl"].endswith("%(id)s.%(ext)s")
    assert opts["download_archive"].endswith(".ytdlarchive")

    # archive.org metadata construction
    meta = TubeUp.create_archive_org_metadata_from_youtubedl_meta({
        "title": "Consumer Test Video",
        "webpage_url": "https://www.youtube.com/watch?v=abc123",
        "extractor_key": "Youtube",
        "uploader": "tester",
        "upload_date": "20260102",
        "tags": ["alpha", "beta"],
        "description": "line1\nline2",
    })
    assert meta["mediatype"] == "movies"
    assert meta["collection"] == "opensource_movies"
    assert meta["creator"] == "tester"
    assert meta["date"] == "2026-01-02"
    assert meta["year"] == "2026"
    assert meta["description"] == "line1<br>line2"
    assert meta["originalurl"] == "https://www.youtube.com/watch?v=abc123"
    assert meta["scanner"] == "TubeUp Video Stream Mirroring Application 2026.5.8"

    # identifier / file helpers
    assert sanitize_identifier("twitch:vod-v181464551") == "twitch-vod-v181464551"
    assert sanitize_identifier("youtube-Xy2jZABDB40") == "youtube-Xy2jZABDB40"

    probe = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                         "tubeup-empty-probe.txt")
    with open(probe, "w", encoding="utf-8"):
        pass
    try:
        assert check_is_file_empty(probe) is True
    finally:
        os.remove(probe)

    print("OK: tubeup 2026.5.8 consumer API test passed")


if __name__ == "__main__":
    main(sys.argv)
