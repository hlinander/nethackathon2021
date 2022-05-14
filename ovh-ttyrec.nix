#with import /home/herden/sw/nix {};
with import (builtins.fetchTarball {
  # Descriptive name to make the store path easier to identify
  name = "nixos-unstable-nethack";
  # Commit hash for nixos-unstable as of 2018-09-12
  url = "https://github.com/nixos/nixpkgs/archive/16b0f078907b39fcdf1c938342c3529a49e3cafb.tar.gz";
  # Hash obtained using `nix-prefetch-url --unpack <url>`
  sha256 = "0fk2higg1ll908ba540gd284kkn6svfz2gvjj4p60zzq756p9835";
}) {};

stdenv.mkDerivation rec {
  pname = "ovh-ttyrec";
  version = "0.1.0";

  src = fetchgit {
    url = "https://github.com/ovh/ovh-ttyrec.git";
    sha256 = "1zfylqmibxj1zfwan5hygrmz4ksg2k70kdkqkmm6chiinf76pd7p";
    rev = "a13ca7402d444637fe9e6cfecd8efaa97657b5f0";
  };

  nativeBuildInputs = [
    gcc
  ];

  # configurePhase = '' '';
  # buildPhase = ''
  #   ./local_ghetto_build.sh
  #   '';
  # installPhase = ''
  #   mkdir -p $out/
  #   cp halloffame $out/
  #   cp *.wav $out/
  # '';
}
