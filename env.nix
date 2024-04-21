with import (fetchTarball "https://github.com/NixOS/nixpkgs/archive/nixos-unstable.tar.gz") {};

buildEnv {
    name="vinst";
paths = [ (python3.withPackages(ps: with ps; [
    sqlalchemy
    psycopg2
    protobuf
    ipython
    numpy
    readchar
    pyte
    dotmap
    dacite
    python-lsp-server
    ipython
    requests
    openai
])) protobuf ];
}
