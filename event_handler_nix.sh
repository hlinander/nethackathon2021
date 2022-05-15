#!/usr/bin/env bash
nix-build env.nix -o penv
penv/bin/python event_handler.py $@
