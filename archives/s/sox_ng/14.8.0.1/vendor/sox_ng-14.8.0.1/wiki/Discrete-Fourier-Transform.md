# Discrete Fourier Transform

## Use of DFTs in SoX

SoX uses the Discrete Fourier Transform for

### `fir`, `firfit`, `hilbert`, `loudness`, `rate`, `sinc` and `vad`

These use `lsx_safe_rdft()`, a fast power-of-two-size routing in `fft4g.[ch]`

### `spectrogram`

Used `fft4g` for power-of-two-size DFTs and has its own internal
non-power-of-two `rdft_p()` routine which is a hundred times slower.

If it is available, it now uses FFTW for both.

## 64-bit double precision is necessary

It may seem that single-precision floats might be enough for SoX
with their 25-bit precision but on 2025-11-29 Sergei Steshenko makes
an exhaustive analysis of the necessary precision in DFT work for audio:

On 2025-11-29 [Sergei Steshenko writes](https://sourceforge.net/p/sox/mailman/message/59266477):
> FT (Fourier Transform - not necessarily DFT - Discrete Fourier Transform) is a subset of transforms in which the function to be transformed is decomposed, i.e. presented as a sum of orthogonal functions - see https://en.wikipedia.org/wiki/Orthogonal_functions .
>
> And on DFT specifically, see, for example, "Nailing Fourier Series and Orthogonal Decompositions" - https://medium.com/@ivethium/nailing-fourier-series-and-orthogonal-decompositions-ff94b9d7476a . And/or https://fftw.org/fftw3_doc/What-FFTW-Really-Computes.html#What-FFTW-Really-Computes .
>
> So, in DFT the 'cos' and 'sin' components are the set of orthogonal functions to do the decomposition on. I emphasize the point - each cos(2 * pi * Bn / N) and sin(2 * pi * Bn / N) (Bn is bin number and N is number of points DFT) is orthogonal each other when Bn is different - this is by definition of orthogonality.
>
> Mathematically the above cos(2 * pi * Bn / N) and sin(2 * pi * Bn / N) are orthogonal, but computationally they are not necessarily orthogonal because of insufficient number of bits.
>
> If we take DFT bin number 0 (Bn is 0), cos(2 * pi * Bn / N) becomes cos(0) which is 1, and if bin number 1 (Bn is 1) cos(2 * pi * Bn / N) becomes cos(2 * pi  / N) . With large enough N because of limited number of bits the 2 * pi  / N will become effectively 0 and thus cos(0) will become equal to cos(2 * pi  / N), thus instead of two orthogonal (i.e. different) functions we'll have just ONE (cos(0)) function.
>
> So, we'll break the orthogonality assumption and thus we will NOT be performing DFT.
>
> A quick check in Julia:
>
> "
>
> julia> let; x::Float32 = 1.0 / 4096; cos(x) end
> 1.0f0
>
> julia> let; x::Float32 = 1.0 / 2048; cos(x) end
> 0.9999999f0
> ",
>
> i.e. N = 4096 is already  too much for 32 bit FP numbers.
>
> ...
>
> I think I'll be able to find other FFT libraries which work with non-power of 2 numbers 64 bit floats.

> To emphasize the point(s).
>
> If/when we perform spectral analysis, we are interested in two (three) things:
>
> 1) presence/absence of spectral components;
>
> 2) magnitude of spectral components;
>
> 3) maybe phase of spectral components.
>
> The issue I described causes lack of resolution when looking for spectral components. I.e. not sufficient number of bits in DFT prevents properly detecting spectral components. With 32 bit FP numbers signal itself has ~23 bit resolution, but frequency domain resolution is less than 12 bits.

> And the same kind of test for 64 bit FP numbers:
>
> "
>
> julia> let; x::Float64 = 1.0 / (2^27); cos(x) end
> 1.0
>
> julia> let; x::Float64 = 1.0 / (2^26); cos(x) end
> 0.9999999999999999
>
> julia> 2.0^26 / 44100
> 1521.742947845805
>
> ",
>
> i.e. 27 bits is too much. Which means that for audio applications 64 bit floats are quite OK as long as buffer size is less than 1522 seconds @ 44100Hz sample rate.

On 2025-11-29 [prof-spock writes]():

> Sergei's observation can also be analyzed as follows:
>
> We are looking for DFT bin counts n, where cos(0) - cos(1/n) is
> less than the machine precision (indicated by the number of bits in
> the mantissa).  In that case cos(1/n) does not differ enough from
> cos(0) so that the difference is zero (this is referred to as
> "numerical cancellation" by the way).
>
> For floats the machine precision m is 2^(-24), for doubles it
> is 2^(-53).
>
> So we have:
>
>     cos(0) - cos(2*pi/n) = 1 - cos(2*pi/n) < m
>     ==> n > 2*pi/arccos(1 - m)
>
> For floats this leads to n > 18198, for doubles n > 421657428.

and for 31-bit fixed point n > 205887.

## See also

* [*The 1d Discrete Fourier Transform*](https://fftw.org/fftw3_doc/The-1d-Discrete-Fourier-Transform-_0028DFT_0029.html) at FFTW.org
