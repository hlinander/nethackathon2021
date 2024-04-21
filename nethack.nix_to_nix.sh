#!/usr/bin/env bash
set -e

has_arg() {
  local search=$1
  shift
  for arg in "$@"; do
    if [ "$arg" = "$search" ]; then
      return 0
    fi
  done
  return 1
}

# Define variables
pname="nethack"
version="0.1.1"
lua_archive="lua-5.4.2.tar.gz"
lua_url="http://www.lua.org/ftp/$lua_archive"
user_dir="$HOME/.config/nethack"
#bin_path=$(which coreutils) # Adjust with actual path to `less` and other required binaries
out="$(pwd)/build"

if has_arg "configure" "$@"; then
	pushd client/NetHack/sys/unix
	./setup.sh hints/linux
	popd
	pushd client/NetHack
	touch src/mon.c
	mkdir -p lib
	(cd lib && wget ${lua_url} && tar xzf "$lua_archive" && rm -fr "$lua_archive")
	CC=clang make PREFIX=$(pwd)/build "-j$(nproc)" "-l$(nproc)"
	popd
fi

#  makeFlags = "PREFIX=$(out)";
userDir="$out/.config/nethack"
#  binPath = lib.makeBinPath [ coreutils less ];
binPath="$out"

# Build
#pushd client/NetHack
#CC=clang make PREFIX=$(pwd)/build "-j$(nproc)" "-l$(nproc)"
#popd

if has_arg "rust" "$@"; then
	pushd client/rust/nethack-rs
	echo $(pwd)
	python regen.py
	popd
	pushd client/rust
	cargo build
	popd
fi

if has_arg "build" "$@"; then
	pushd client/NetHack
	CC=clang make PREFIX=$out "-j$(nproc)" "-l$(nproc)"
	popd
fi


if has_arg "install" "$@"; then
	pushd client/NetHack
	make PREFIX=$out install
	popd

	# Patch
	#; sed -e '/^ *cd /d' -i client/NetHack/sys/unix/nethack.sh
	# sed -e '/define CHDIR/d' -i client/NetHack/include/config.h

	# Fixup
	echo "POSTINSTALL"
	mkdir -p $out/games/lib/nethackuserdir
	for i in xlogfile logfile perm record save; do
	  mv $out/games/lib/nethackdir/$i $out/games/lib/nethackuserdir
	done
	touch $out/testfile
	mkdir -p $out/bin
	cat <<EOF >$out/bin/nethack
#!/usr/bin/env bash
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
export PYTHONPATH=$out/games/lib/nethackdir
$out/games/nethack
EOF
	chmod +x $out/bin/nethack
fi
#install -Dm 555 util/{makedefs,dgn_comp,lev_comp} -t $out/libexec/nethack/

if has_arg "run" "$@"; then
	(cd /tmp/sko/bin/ && DB_USER_ID=1 ./nethack)
fi
