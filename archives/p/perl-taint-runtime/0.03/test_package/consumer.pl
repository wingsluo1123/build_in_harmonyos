BEGIN { @INC=split /:/,$ENV{PERL5LIB}; }
use strict;use warnings;use Taint::Runtime qw(taint_start taint_stop taint_enabled taint untaint is_tainted taint_deeply $TAINT);
die 'wrong version' unless $Taint::Runtime::VERSION eq '0.03';
die 'foreign installed module' unless index($INC{'Taint/Runtime.pm'},$ENV{TAINT_RUNTIME_MODULE_ROOT}.'/')==0;
taint_start();die 'taint enable' unless taint_enabled();my $value="Harmony\0UTF8";my $tainted=taint($value);die 'taint semantics' unless is_tainted($tainted) && !is_tainted($value);
my $clean=untaint($tainted);die 'untaint bytes' unless $clean eq $value && !is_tainted($clean);
my $graph={a=>['payload']};$graph->{self}=$graph;taint_deeply($graph);die 'deep taint cycle' unless is_tainted($graph->{a}[0]);
taint_stop();die 'process-local stop' if taint_enabled();{local $TAINT=1;die 'lexical taint state' unless taint_enabled();}die 'restore lexical state' if taint_enabled();
die 'foreign installed XS' unless grep {index($_,$ENV{TAINT_RUNTIME_XS_ROOT}.'/auto/Taint/Runtime/')==0 && /\/Runtime\.so$/} @DynaLoader::dl_shared_objects;
print "CONSUMER_TEST_COUNT=2\nCONSUMER_TEST_PASS=2/2\n";
