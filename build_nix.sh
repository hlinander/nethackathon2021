#!/usr/bin/env bash
nix-shell nethack.nix --run 'out=$(pwd)/build phases="configurePhase postPatch buildPhase installPhase postInstall" genericBuild'
