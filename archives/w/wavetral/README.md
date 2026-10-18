# Wavetral

> Wavetral converts single-cycle waveforms and additive spectra between formats used by synthesizers.

## Introduction

Wavetral is a command-line utility for moving single-cycle waves between audio files, plain-text value lists, Csound ftables, Yoshimi scripts, and Waldorf Microwave II/XT dumps. It can also resample waves and change the number of harmonics while converting.

## OHOS Adaptation

The upstream CMake project is built as an application. Conan supplies Boost, FFTW, libsndfile, and libsamplerate through `CMakeDeps` and `PkgConfigDeps`. The packaged result is `bin/wavetral`.

## Dependencies

| Dependency | Version |
|---|---|
| boost | 1.90.0.4 |
| fftw | 3.3.11 |
| libsndfile | 1.2.2 |
| libsamplerate | 0.2.2 |

## Verification

```bash
wavetral --version
wavetral -i sine8.txt -t wave -o spectrum.txt -T harm -s 4
```

## References

- [Source repository](https://github.com/jeanette-c/wavetral)
