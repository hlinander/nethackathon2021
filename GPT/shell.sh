nix-shell -p "python3.withPackages(p:[ p.openai p.numpy p.tqdm p.transformers p.ffmpeg-python p.click p.pyaudio p.pydub p.torch-bin p.python-lsp-server p.pyclip])" 'openai-whisper.override { torch = python3.pkgs.torch-bin; }' tts espeak mimic
