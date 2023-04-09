#!/usr/bin/env bash

GOOS=linux GOARCH=amd64 go build . 
scp -P 2020 nethackinit eracce@nh.hampe.nu: