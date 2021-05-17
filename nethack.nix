#{
#  #pkgs ? import (fetchTarball "https://github.com/NixOS/nixpkgs-channels/archive/b58ada326aa612ea1e2fb9a53d550999e94f1985.tar.gz") {}
#  pkgs ? import (fetchTarball "https://github.com/NixOS/nixpkgs/archive/refs/tags/20.09.tar.gz") {}
#}:
#with import <nixpkgs> {};
#{
#    rustPlatform,
#    stdenv,
#    fetchgit,
#    breakpointHook,
#    clang,
#    ncurses,
#    protobuf
#}:
with import /home/herden/sw/nix {};
stdenv.mkDerivation rec {
  pname = "nethack";
  version = "0.1.0";

  src = fetchgit {
    url = "https://github.com/hlinander/nethackathon2021.git";
    deepClone = true;
    sha256 = "19z4azwfjxbmhxl6sqslbhnh6rsz5dibsw2h369r67q1mxjy3p2v";
    rev = "5abff8fae471485276fafde72867b744e6968ff6";
  };

  lua = fetchurl {
      url = http://www.lua.org/ftp/lua-5.4.2.tar.gz;
      sha256 = "0ksj5zpj74n0jkamy3di1p6l10v4gjnd2zjnb453qc6px6bhsmqi";
  };

  cargoDeps = rustPlatform.fetchCargoTarball {
      inherit src;
      sourceRoot = "${src.name}/client/rust";
      #sourceRoot = "client/rust";
      #sourceRoot = "client/rust";
      sha256 = "1k9l3mzi0v24052dalcgjsrdz9x2xr6xrcg4f9ly3hzp3lyp0bhr";
    };

  cargoRoot = "client/rust";

  nativeBuildInputs = [
    groff
    utillinux
    curl
    breakpointHook
    clang
    ncurses
    protobuf
  ] ++ (with rustPlatform; [
    cargoSetupHook
    rust.cargo
    rust.rustc
  ]);
  # buildInputs = [
  #   pkgs.clang
  #   pkgs.ncurses
  #   pkgs.rustc
  #   pkgs.cargo
  #   pkgs.protobuf
  # ];
  PROTOC = "${protobuf}/bin/protoc";
  #PREFIX="$(out)";

  configurePhase = ''
  '';

  makeFlags = "PREFIX=$(out)";
  userDir = "~/.config/nethack";
  binPath = lib.makeBinPath [ coreutils less ];
  #OUTPUTDIR="${out}";

  buildPhase = ''
    cd client/rust
    cargo build
    cd ../NetHack
    mkdir -p lib
    (cd lib; tar xzf ${lua})
    ls lib
    (cd sys/unix/; ./setup.sh hints/linux)
    CC=clang make PREFIX=$out "-j$NIX_BUILD_CORES" "-l$NIX_BUILD_CORES"
    #CC=clang make fetch-lua
  '';

  installPhase = ''
  '';

  postPatch = ''
      sed -e '/^ *cd /d' -i client/NetHack/sys/unix/nethack.sh
      sed -e '/define CHDIR/d' -i client/NetHack/include/config.h
      '';

  postInstall = ''
    mkdir -p $out/games/lib/nethackuserdir
    for i in xlogfile logfile perm record save; do
      mv $out/games/lib/nethackdir/$i $out/games/lib/nethackuserdir
    done
    mkdir -p $out/bin
    cat <<EOF >$out/bin/nethack
    #! ${stdenv.shell} -e
    PATH=${binPath}:\$PATH
    if [ ! -d ${userDir} ]; then
      mkdir -p ${userDir}
      cp -r $out/games/lib/nethackuserdir/* ${userDir}
      chmod -R +w ${userDir}
    fi
    RUNDIR=\$(mktemp -d)
    cleanup() {
      rm -rf \$RUNDIR
    }
    #trap cleanup EXIT
    cd \$RUNDIR
    echo \$RUNDIR
    for i in ${userDir}/*; do
      ln -s \$i \$(basename \$i)
    done
    for i in $out/games/lib/nethackdir/*; do
      ln -s \$i \$(basename \$i)
    done
    $out/games/nethack
    EOF
    chmod +x $out/bin/nethack
    #install -Dm 555 util/{makedefs,dgn_comp,lev_comp} -t $out/libexec/nethack/
  '';
}
