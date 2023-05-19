{
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
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
          (python3.withPackages(p:[ p.openai p.numpy p.tqdm p.transformers p.ffmpeg-python p.click p.pyaudio p.pydub p.torch-bin p.python-lsp-server p.pyclip])) 
          (openai-whisper.override { torch = python3.pkgs.torch-bin; }) 
          tts 
          espeak 
          mimic          
          nixfmt
        ];
    in {
      devShells.x86_64-linux.default = pkgs.mkShellNoCC {
        buildInputs = devinputs;
         };
    };
}
