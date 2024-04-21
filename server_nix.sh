#!/usr/bin/env bash
nix-build env.nix -o penv
# penv/bin/python -m venv --system-site-packages penv_with_openai
# penv_with_openai/bin/pip install -r telefon/requirements.txt
penv/bin/python vinst.py
