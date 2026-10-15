# Mult

This is about the `mult` field of `sox_effect_t` and
the `SOX_EFF_GAIN` flag of effects, which implement the
`gain -h` - `gain -r` mechanism.

According to the manual:

> The -r option is used in conjunction with a prior invocation of
> gain with the -h option - see below for details.
>
> The -h option is used to apply gain to provide headroom for
> subsequent processing. For example, with
> 
>    sox_ng in.au out.au gain -h bass +6
> 
> 6dB of attenuation is applied prior to the bass boosting effect,
> ensuring that it does not clip. Of course, with bass, it is
> obvious how much headroom is needed but, with other effects (e.g.
> rate, dither), it is not always as clear. Another advantage of
> using gain -h rather than an explicit attenuation is that, if the
> headroom is not used by subsequent effects, it can be reclaimed
> with gain -r, for example:
> 
>    sox_ng in.au out.au gain -h bass +6 rate 44100 gain -r
> 
> The above effects chain guarantees never to clip nor amplify; it
> attenuates if necessary to prevent clipping, but by only as much
> as is needed to do so.

It seems to do this by each effect knowing the most it might increase
(or decrease) the maximum amplitude and each signal path (a `sox_signal_info_t`)
containing a

    double  * mult;    /**< Effects headroom multiplier; may be null */

Effects that know how much gain they will apply, at the end of their `start()`,
divide `*effp->in_signal.mult` by whatever their linear amplification is,
and this pointer is copied forwards from each effect's input to its output
unless the effect has `SOX_EFF_GAIN` in its flags.
Confusingly, `SOX_EFF_GAIN` means "I *don't* support what `-h` and `-r` need
because I don't know how much I might change the maximum amplitude by and
I neither copy the pointer nor modify what it points to".

That pointer is set initially to point to the fixed gain of `gain -h`;
if there isn't a `gain -h` early in the effects chain, or if there's a
`gain` without the `-h` option, it is NULL.
A `gain -r` later on in the chain then looks at the pointer and, if it's
still pointing at the volume of `gain -h`

Strangely, `gain` itself has `SOX_EFF_GAIN` and doesn't support automatic
gain reduction and recovery. `vol` is the same; you would have thought that
would know how much it amplifies or attenuates by!

So, here's how it might work:

    sox in.au out.au gain -h bass +6 gain -r

* When `gain -h` is started, it sets its `effp->out_signal.mult` to point
to its own volume control, initially with a setting of 1
* When `bass +6` is started, if divides what its `effp->in_signal.mult`
  points to by `dB_to_linear(+6)`
* When `gain -r` is started, it looks at *its* `effp->in_signal.mult` and,
  if it is not NULL, and what it points to hasn't gone `>= 1`, it sets
  its own volume control to one over that.
  Not sure why `-r` is needed; `-h` has already had its volume adjusted
  by `bass`.
