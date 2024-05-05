#!/usr/bin/env bash
SESSION="nethackathon"

# Start a new tmux session
docker start nh2024
source ./openai_key.sh
tmux new-session -d -s $SESSION
tmux new-window -t $SESSION:1 -n 'Window 1' -d './server_nix.sh; bash'
tmux new-window -t $SESSION:2 -n 'Window 2' -d './event_handler_nix.sh; bash'
tmux new-window -t $SESSION:3 -n 'Window 3' -d 'pushd nethack-web/go; go run .; bash'
tmux new-window -t $SESSION:4 -n 'Window 4' -d 'pushd oracle-main-service; go run .; bash'
# tmux new-window -t $SESSION:5 -n 'Window 5' -d 'pushd oracle-worker; go run . ; bash'

# Attach to the session
tmux attach-session -t $SESSION
