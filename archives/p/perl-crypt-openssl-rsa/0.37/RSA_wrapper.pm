package Crypt::OpenSSL::RSA;

# HarmonyOS SELinux workaround wrapper for Crypt::OpenSSL::RSA
#
# OHOS SELinux (hishell_hap:s0) blocks dlopen() of .so files,
# making the original XS module (RSA.so) unloadable at runtime.
# This pure-Perl wrapper delegates RSA operations to a compiled
# C helper (rsa_helper) that links libssl/libcrypto at startup,
# bypassing the SELinux dlopen restriction.
#
# API-compatible with Crypt::OpenSSL::RSA 0.37

use strict;
use warnings;
use MIME::Base64 qw(encode_base64 decode_base64);
use IPC::Open3 qw(open3);
use Symbol qw(gensym);
use File::Spec;

our $VERSION = '0.37';

# Default padding and hash modes
my %DEFAULT = (
    padding => 'pkcs1',
    hash    => 'sha256',
);

# Find the rsa_helper binary
sub _find_helper {
    return $ENV{RSA_HELPER} if $ENV{RSA_HELPER} && -x $ENV{RSA_HELPER};
    for my $dir (split /:/, $ENV{PATH} || '') {
        my $path = File::Spec->catfile($dir, 'rsa_helper');
        return $path if -x $path;
    }
    my $default = File::Spec->catfile($ENV{HOME} // '/storage/Users/currentUser', 'usr', 'local', 'bin', 'rsa_helper');
    return $default if -x $default;
    die "rsa_helper binary not found. Set RSA_HELPER env var to its path.\n";
}

# Run rsa_helper and capture output
sub _run_helper {
    my ($self, @args) = @_;
    my $helper = _find_helper();
    my $stdin_data = '';

    # Extract stdin data (last hash element with key '__stdin__')
    if (@args && ref($args[-1]) eq 'HASH' && exists $args[-1]{__stdin__}) {
        $stdin_data = $args[-1]{__stdin__};
        pop @args;
    }

    my ($stdin, $stdout, $stderr);
    $stderr = gensym();
    my $pid = open3($stdin, $stdout, $stderr, $helper, @args);

    if ($stdin_data ne '') {
        print $stdin $stdin_data;
    }
    close $stdin;

    local $/;
    my $out = <$stdout>;
    my $err = <$stderr>;
    waitpid($pid, 0);
    my $rc = $? >> 8;

    if ($err && $err =~ /\S/) {
        die "rsa_helper error: $err" unless $rc == 0;
    }

    # Remove trailing newline
    $out =~ s/\s+$// if defined $out;

    return wantarray ? ($out, $rc) : $out;
}

# Constructor: generate new key
sub generate_key {
    my ($class, $bits) = @_;
    $bits //= 2048;
    my $pem = _run_helper(undef, 'generate', $bits);
    my $pub = _run_helper(undef, 'pubkey', $pem);
    my $self = bless {
        private_pem => $pem,
        public_pem  => $pub,
        padding     => $DEFAULT{padding},
        hash        => $DEFAULT{hash},
        is_private  => 1,
        is_public   => 1,
    }, $class;
    return $self;
}

# Constructor: from public key PEM
sub new_public_key {
    my ($class, $pem) = @_;
    my $self = bless {
        public_pem  => $pem,
        private_pem => undef,
        padding     => $DEFAULT{padding},
        hash        => $DEFAULT{hash},
        is_private  => 0,
        is_public   => 1,
    }, $class;
    return $self;
}

# Constructor: from private key PEM
sub new_private_key {
    my ($class, $pem) = @_;
    my $pub = _run_helper(undef, 'pubkey', $pem);
    my $self = bless {
        private_pem => $pem,
        public_pem  => $pub,
        padding     => $DEFAULT{padding},
        hash        => $DEFAULT{hash},
        is_private  => 1,
        is_public   => 1,
    }, $class;
    return $self;
}

# Sign a message
sub sign {
    my ($self, $message) = @_;
    die "Private key required for signing\n" unless $self->{private_pem};
    my $sig_b64 = _run_helper($self, 'sign', $self->{hash}, $self->{private_pem},
                              { __stdin__ => $message });
    return decode_base64($sig_b64);
}

# Verify a signature
sub verify {
    my ($self, $message, $signature) = @_;
    die "Public key required for verification\n" unless $self->{public_pem};
    my $sig_b64 = encode_base64($signature, '');
    my ($result, $rc) = _run_helper($self, 'verify', $self->{hash},
                                    $self->{public_pem}, $sig_b64,
                                    { __stdin__ => $message });
    return $rc == 0 ? 1 : 0;
}

# Encrypt with public key
sub encrypt {
    my ($self, $plaintext) = @_;
    die "Public key required for encryption\n" unless $self->{public_pem};
    my $ct_b64 = _run_helper($self, 'encrypt', $self->{padding}, $self->{public_pem},
                             { __stdin__ => $plaintext });
    return decode_base64($ct_b64);
}

# Decrypt with private key
sub decrypt {
    my ($self, $ciphertext) = @_;
    die "Private key required for decryption\n" unless $self->{private_pem};
    my $ct_b64 = encode_base64($ciphertext, '');
    my $pt = _run_helper($self, 'decrypt', $self->{padding}, $self->{private_pem},
                         { __stdin__ => $ct_b64 });
    return $pt;
}

# Get public key PEM
sub get_public_key {
    my ($self) = @_;
    return $self->{public_pem};
}

# Get private key PEM
sub get_private_key_string {
    my ($self) = @_;
    return $self->{private_pem};
}

# Get key size in bytes
sub size {
    my ($self) = @_;
    my $pem = $self->{private_pem} // $self->{public_pem};
    return int(_run_helper($self, 'size', $pem));
}

# Get key size in bits
sub key_size {
    my ($self) = @_;
    return $self->size() * 8;
}

# ---- Padding mode setters ----
sub use_pkcs1_padding       { $_[0]->{padding} = 'pkcs1'; return $_[0]; }
sub use_pkcs1_oaep_padding  { $_[0]->{padding} = 'oaep';  return $_[0]; }
sub use_sslv23_padding      { $_[0]->{padding} = 'pkcs1'; return $_[0]; } # SSLv23 deprecated
sub use_no_padding          { $_[0]->{padding} = 'none';  return $_[0]; }

# ---- Hash mode setters ----
sub use_md5_hash    { $_[0]->{hash} = 'md5';    return $_[0]; }
sub use_sha1_hash   { $_[0]->{hash} = 'sha1';   return $_[0]; }
sub use_sha256_hash { $_[0]->{hash} = 'sha256'; return $_[0]; }
sub use_sha384_hash { $_[0]->{hash} = 'sha384'; return $_[0]; }
sub use_sha512_hash { $_[0]->{hash} = 'sha512'; return $_[0]; }

# Check if module is XS (false for this wrapper)
sub _is_xs { 0 }

1;

__END__

=head1 NAME

Crypt::OpenSSL::RSA - RSA encoding and decoding (HarmonyOS wrapper)

=head1 SYNOPSIS

    use Crypt::OpenSSL::RSA;

    # Generate key pair
    my $rsa = Crypt::OpenSSL::RSA->generate_key(1024);

    # Sign and verify
    my $sig = $rsa->sign("message");
    my $valid = $rsa->verify("message", $sig);

    # Encrypt and decrypt
    my $ct = $rsa->encrypt("secret");
    my $pt = $rsa->decrypt($ct);

    # Export keys
    my $pub_pem = $rsa->get_public_key();
    my $priv_pem = $rsa->get_private_key_string();

=head1 DESCRIPTION

This is a HarmonyOS-compatible wrapper for Crypt::OpenSSL::RSA.
Due to OHOS SELinux restrictions that block dlopen() of shared
libraries, the original Perl XS module cannot be loaded at runtime.
This wrapper delegates RSA operations to a compiled C helper
(rsa_helper) that links against libssl/libcrypto at process startup.

API-compatible with Crypt::OpenSSL::RSA 0.37.

=head1 AUTHOR

OpenDesk HarmonyOS Adaptation

=cut
