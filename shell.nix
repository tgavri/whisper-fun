{ pkgs ? import <nixpkgs> {} }:
  pkgs.mkShell {
    nativeBuildInputs = with pkgs.buildPackages; [ 
      python313
      python313Packages.openai-whisper
      ffmpeg
    ];
}

