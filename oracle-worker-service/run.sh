#!/usr/bin/env bash
nix develop
uvicorn serve:app
