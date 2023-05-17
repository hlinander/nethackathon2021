{
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-22.11";
  outputs = { self, nixpkgs, ... }:
    let
      system = "x86_64-linux";
      pkgs = (import nixpkgs {
        inherit system;
        config = {
          allowUnfree = true;
        };
      });
      devinputs = with pkgs; [
          nixfmt
          gopls
          rust-analyzer
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
      devShells.x86_64-linux.default = pkgs.mkShellNoCC {
        buildInputs = devinputs;
         };
    };
}
