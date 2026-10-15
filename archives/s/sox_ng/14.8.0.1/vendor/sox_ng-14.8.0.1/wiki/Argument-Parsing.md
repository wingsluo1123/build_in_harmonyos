# Argument parsing

SoX first scans the start of the command line processing the global options
and per-file parameters that will apply to the next input file.

Long options that have single-letter equivalents are converted
into those letters and ones that don't are in the first half of
`long_options[]` and their integer index in that table is fed to
a huge `case` statement that switches on that integer.

For example to find out what `--help-format` does, open `sox_ng.c`
and search for `help-format`. It's `long_options[9]` so you then
search for `case 9:` and it calls `usage_format(optstate.arg)`.

When it find the first input filename (or `-n`) it gobbles up
anything that's not an effect name as the input files and the
output file.

Now it breaks the rest of the command line on effect names and colons,
then makes an `argc,argv[]` pair for each series of arguments between
effect names and passes those to the preceding effect's `getopt` function.

How each effect parses what it gets in its `argv[]` is up to it.
Most of them use one of SoX's two argument-parsing mechanisms:
16 use `NUMERIC_PARAMETER/TEXTUAL_PARAMETER` and 10 use the
`GETOPTS_NUMERIC` macros but there is also an Arabian market of
hairy `case` statements, use of stuff from `<string.h>` and
custom-built state machines.

## `*_PARAMETER`

An example of this from `chorus.c` is:


    chorus->gain_in = 0.5;
    chorus->gain_out = 1;
    do {
        chorus_priv_t* p = chorus;
        NUMERIC_PARAMETER(gain_in, -1.0, 1.0);
        NUMERIC_PARAMETER(gain_out,-1.0, 1.0);
    } while (0);

which scans the local `argv[0]` for a floating point number
The first parameter to the macro can also be of an integral type
in which case it stores the integer of the next lowest absolute value.

Its companion, `TEXTUAL_PARAMETER`, looks the argument up in a table
of enumerated values, matching abbreviations of the full names if
they uniquely identify one (like `sin` for `sine`).

Note that `synth.c` has its own variant of `NUMERIC_PARAMETER` that
takes percentages and divides the argument by 100.

## `GETOPT_*`

An example of this from `dither.c` is:

    lsx_getopt_t optstate;
    lsx_getopt_init(argc, argv, "+aSsf:p:", NULL, lsx_getopt_flag_none, 1, &optsta
te);
    
    while ((c = lsx_getopt(&optstate)) != -1) switch (c) {
      case 'a': p->auto_detect = sox_true; break;
      case 'S': p->alt_tpdf = sox_true; break;
      case 's': p->filter_name = Shape_shibata; break;
    case 'f':
      p->filter_name = lsx_enum_option(c, optstate.arg, filter_names);
      if (p->filter_name == INT_MAX)
        return SOX_EOF;
      break;
      GETOPT_NUMERIC(optstate, 'p', precision, 1, 24)
    default: /* invalid option or missing obligatory argument */
      if (optstate.ind > argc) {
        lsx_fail("-%c what?", optstate.opt);
      } else {
        lsx_fail("invalid option `-%c'", optstate.opt);
        return lsx_usage(effp);
      }
      return SOX_EOF;
    }

where the `GETOPT_NUMERIC` defines a `-p` flag taking a value between 1 and 24
which it stores in `p->precision` and the exact names of the fields of `priv_t`
that are used in `GETOPT_NUMERIC` are important because they are
what is reported as having an invalid value in range error messages;
they should correspond to the name of the parameter in the effect's usage
line and the first line of its manual entry.

A variant is `GETOPT_LOCAL_NUMERIC` where, instead of giving a `priv_t`
member name, you give the name of a local variable which it fills in and
which you will presumably use subsequently to set values in the effect's
private data.

They use the local `argc` and `argv`, increment `argn` if an in-range
number was found at `argv[argn]`, `return SOX_EOF` if it's out of range
or has trailing garbage, or `break` on anything else so that
missing parameters keep their default values.

These both parse the following argument as a double-precision floating point
number but the target variable can also be an integral type, and it will be
converted accordingly.
