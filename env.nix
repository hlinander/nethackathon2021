with import <nixpkgs> {};

python38.withPackages(ps: with ps; [
    sqlalchemy
    psycopg2
    protobuf
])
