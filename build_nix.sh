#!/usr/bin/env bash
nix-shell --pure nethack.nix --run 'out=$(pwd)/build phases="configurePhase postPatch buildPhase installPhase fixupPhase" genericBuild'
chmod -R g+rwx build/
