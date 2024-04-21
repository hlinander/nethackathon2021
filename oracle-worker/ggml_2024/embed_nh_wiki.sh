ls nhwiki/chunked* | grep -v .bin | xargs -I{} result/bin/embedding -m models/ggml-sfr-embedding-mistral-q4_k_m.gguf -f {} -b 512 -ngl 40
