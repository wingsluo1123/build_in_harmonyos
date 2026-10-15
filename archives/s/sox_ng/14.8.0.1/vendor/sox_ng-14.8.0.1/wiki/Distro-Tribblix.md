# Distro Tribblix

[Tribblix](http://www.tribblix.org) packages sox_ng-14.4.4 (calling it 14.4.4.0)

## TODO

Instead of `ln -s sox_ng sox` in [`fixit`](https://github.com/tribblix/build/blob/master/TRIBsox/fixit) it should probably
`./configure --enable-replace`, which will make the "play", "rec" and "soxi"
links as well as links to the manual pages.
