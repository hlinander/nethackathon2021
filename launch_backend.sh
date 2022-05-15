#!/usr/bin/env bash
tmux \
    new-session  'bash -c "./server_nix.sh"' \; \
    split-window 'bash -c "./event_handler_nix.sh"' \; \
#     split-window -h 'watch squeue --me' \; \
#     select-pane -t 0 \; \
#     split-window -h 'pushd ~/entropy_variance/; bash' \; \
