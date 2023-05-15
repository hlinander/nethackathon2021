with import <nixpkgs> {};

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
])) protobuf ];
}
