with import (fetchTarball https://nixos.org/channels/nixos-unstable/nixexprs.tar.xz) {};
#with import <nixpkgs> {};
#with import (fetchTarball https://github.com/NixOS/nixpkgs/archive/8dd8bd8be74.tar.gz) {};

#with import (fetchTarball https://github.com/NixOS/nixpkgs/archive/6efc186e6079ff3f328a2497ff3d36741ac60f6e.tar.gz) {};
stdenv.mkDerivation rec {
  pname = "nethack";
  version = "0.1.1";

  src = builtins.fetchGit {
    url = "ssh://git@github.com/hlinander/nethackathon2021.git";
    rev = "76f96fb2f64a7654eed2af9ea9a31da1cc5fc4fd";
  };

  lua = fetchurl {
      url = http://www.lua.org/ftp/lua-5.4.2.tar.gz;
      sha256 = "0ksj5zpj74n0jkamy3di1p6l10v4gjnd2zjnb453qc6px6bhsmqi";
  };

  # cargoDeps = rustPlatform.fetchCargoTarball {
  #     inherit src;
  #     sourceRoot = "source/client/rust";
  #     sha256 = "0y5kyq2347pdmhmjcnshkgyd53m2ws3na25dfis603din6bskn3n";
  #   };

  cargoDeps = rustPlatform.importCargoLock {
    # lockFile = source/client/rust/Cargo.lock;
    lockFile = ./client/rust/Cargo.lock;
  };

  cargoRoot = "client/rust";

  nativeBuildInputs = [
    gdb
    groff
    utillinux
    curl
    breakpointHook
    #gcc
    clang
    ncurses
    protobuf
    python3
    rust-bindgen
    rustfmt
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
    pushd client/NetHack
    touch src/mon.c
    mkdir -p lib
    (cd lib; tar xzf ${lua})
    popd
  '';

  makeFlags = "PREFIX=$(out)";
  userDir = "~/.config/nethack";
  binPath = lib.makeBinPath [ coreutils less ];

  buildPhase = ''
    pushd client/NetHack
    CC=clang make PREFIX=$out "-j$NIX_BUILD_CORES" "-l$NIX_BUILD_CORES" || true
    popd
    pushd client/rust/nethack-rs
    python3 regen.py
    popd
    pushd client/rust
    cargo build
    popd
    pushd client/NetHack
    CC=clang make PREFIX=$out "-j$NIX_BUILD_CORES" "-l$NIX_BUILD_CORES"
    popd
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

  fixupPhase = ''
    echo "POSTINSTALL"
    mkdir -p $out/games/lib/nethackuserdir
    for i in xlogfile logfile perm record save; do
      mv $out/games/lib/nethackdir/$i $out/games/lib/nethackuserdir
    done
    touch $out/testfile
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
