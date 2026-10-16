/*
 * Consumer test script for the installed yorick interpreter.
 *
 * Exercises real interpreter + numeric-library functionality as a consumer
 * would use it: scalar arithmetic, array reductions, column-major matrix
 * indexing, and an FFT round-trip through the bundled fft package.
 * Prints YORICK_CONSUMER_OK on success; any mismatch increments nbad and
 * aborts (test.sh asserts a zero exit code AND the marker).
 */
nbad= 0;

/* scalar arithmetic */
if (2+3 != 5)        { write, "FAIL arith"; nbad= nbad+1; }
if (abs(-7) != 7)    { write, "FAIL abs";   nbad= nbad+1; }

/* array reductions */
a= [1,2,3,4];
if (sum(a) != 10)          { write, "FAIL sum";   nbad= nbad+1; }
if (max([2,9,4]) != 9)     { write, "FAIL max";   nbad= nbad+1; }
if (min([2,9,4]) != 2)     { write, "FAIL min";   nbad= nbad+1; }
if (anyof([0,0,3]) != 1)   { write, "FAIL anyof"; nbad= nbad+1; }

/* column-major matrix indexing: [[1,2],[3,4]] has columns (1,2) and (3,4) */
m= [[1,2],[3,4]];
if (m(1,1) != 1) { write, "FAIL matrix 1,1"; nbad= nbad+1; }
if (m(2,1) != 2) { write, "FAIL matrix 2,1"; nbad= nbad+1; }
if (m(1,2) != 3) { write, "FAIL matrix 1,2"; nbad= nbad+1; }
if (m(2,2) != 4) { write, "FAIL matrix 2,2"; nbad= nbad+1; }

/* numeric library: FFT forward + inverse round-trip must reproduce the input */
x= [1.,2.,3.,4.];
z= fft(fft(x), -1) / 4.;
if (abs(z-x)(max) > 1.e-9) { write, "FAIL fft roundtrip"; nbad= nbad+1; }

if (nbad) error, "yorick consumer test failed";

write, "YORICK_CONSUMER_OK";
