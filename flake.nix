{
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-23.11";
  # inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  inputs.fenix = {
    url = "github:nix-community/fenix";
    inputs.nixpkgs.follows = "nixpkgs";
  };
  outputs = { self, nixpkgs, fenix, ... }:
    let
      system = "x86_64-linux";
      pkgs = (import nixpkgs {
        inherit system;
        config = {
          allowUnfree = true;
        };
      });
      rustToolchain = fenix.packages."${system}".stable;
      devinputs = with pkgs; [
          nixfmt
          gopls
          openssl
          pkg-config
        (rustToolchain.withComponents [
          "cargo"
          "rustc"
          "rust-src"
          "rustfmt"
          "clippy"
        ])
        fenix.packages."${system}".rust-analyzer
          # rust-analyzer
          (nodePackages.typescript-language-server)
          (python3.withPackages (p: [
            p.python-lsp-server
            p.numpy
            p.plotext
            p.ipython
            p.black
            p.flake8
            p.snakeviz
            p.pandas
            p.matplotlib
            p.psycopg
            p.pytest
          ]))
        ];
    in {
      devShells.x86_64-linux.default =
        (pkgs.mkShell.override { stdenv = pkgs.llvmPackages_14.stdenv; }) {
          buildInputs = devinputs;
          nativeBuildInputs = [ pkgs.cudatoolkit ];
          shellHook = ''
            export EDITOR=hx

            # export CUDA_PATH=${pkgs.cudatoolkit}
          '';
        };
      # devShells.x86_64-linux.default = pkgs.mkShellNoCC {
      #   buildInputs = devinputs;
      #    };
    };
}
