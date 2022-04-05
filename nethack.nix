with import (fetchTarball https://nixos.org/channels/nixos-unstable/nixexprs.tar.xz) {};
stdenv.mkDerivation rec {
  pname = "nethack";
  version = "0.1.0";

  src = builtins.fetchGit {
    url = "ssh://git@github.com/hlinander/nethackathon2021.git";
    rev = "31bc48597ecb8adc7e79e12304030ce0d135acf4";
  };

  lua = fetchurl {
      url = http://www.lua.org/ftp/lua-5.4.2.tar.gz;
      sha256 = "0ksj5zpj74n0jkamy3di1p6l10v4gjnd2zjnb453qc6px6bhsmqi";
  };

  cargoDeps = rustPlatform.fetchCargoTarball {
      inherit src;
      sourceRoot = "source/client/rust";
      sha256 = "0y5kyq2347pdmhmjcnshkgyd53m2ws3na25dfis603din6bskn3n";
    };

  cargoRoot = "client/rust";

  nativeBuildInputs = [
    gdb
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

  PROTOC = "${protobuf}/bin/protoc";

  configurePhase = ''
    pushd client/NetHack/sys/unix;
    ./setup.sh hints/linux;
    popd;
  '';

  makeFlags = "PREFIX=$(out)";
  userDir = "~/.config/nethack";
  binPath = lib.makeBinPath [ coreutils less ];

  buildPhase = ''
    pushd client/rust
    cargo build
    popd
    pushd client/NetHack
    mkdir -p lib
    (cd lib; tar xzf ${lua})
    ls lib
    cat Makefile
    CC=clang make PREFIX=$out "-j$NIX_BUILD_CORES" "-l$NIX_BUILD_CORES"
    popd
    #CC=clang make fetch-lua
  '';

  installPhase = ''
    pushd client/NetHack
    make PREFIX=$out install
    popd
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
