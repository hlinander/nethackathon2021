with import (fetchTarball https://nixos.org/channels/nixos-unstable/nixexprs.tar.xz) {};
stdenv.mkDerivation rec {
  pname = "nethack";
  version = "0.1.0";

  src = builtins.fetchGit {
    url = "ssh://git@github.com/hlinander/nethackathon2021.git";
    submodules = true;
    rev = "05d7f0db671aef6b0cb2a415b31e29d671567742";
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
  '';

  makeFlags = "PREFIX=$(out)";
  userDir = "~/.config/nethack";
  binPath = lib.makeBinPath [ coreutils less ];

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
