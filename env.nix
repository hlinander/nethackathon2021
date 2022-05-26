with import <nixpkgs> {};

buildEnv {
    name="vinst";
paths = [ (python38.withPackages(ps: with ps; [
    sqlalchemy
    psycopg2
    protobuf
    ipython
    numpy
    readchar
])) protobuf ];
}
