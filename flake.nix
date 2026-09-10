{
  description = "deb2nix — package-agnostic Debian .deb → Nix generator";

  # The generator is MIT. Generated consumer flakes may set allowUnfreePredicate
  # for a single pname. Tim approval 2026-09-10 accepted unfree EULAs for
  # Chrome, Edge, VS Code, Grok Bot, and DisplayLink fixture analysis.
  # This flake does not fetch those vendor blobs at eval time.

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs =
    { self, nixpkgs }:
    let
      systems = [
        "x86_64-linux"
        "aarch64-linux"
      ];
      forAllSystems = nixpkgs.lib.genAttrs systems;
    in
    {
      packages = forAllSystems (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          python = pkgs.python3;
          runtimePath = pkgs.lib.makeBinPath [
            pkgs.dpkg
            pkgs.binutils
            pkgs.gnutar
            pkgs.xz
            pkgs.gzip
            pkgs.bzip2
            pkgs.curl
            pkgs.file
          ];
          deb2nix = python.pkgs.buildPythonApplication {
            pname = "deb2nix";
            version = "0.1.0";
            src = builtins.path {
              path = ./.;
              name = "deb2nix-src";
              filter =
                path: type:
                let
                  base = baseNameOf path;
                in
                !(pkgs.lib.elem base [
                  ".git"
                  "result"
                  "result-nix"
                  "__pycache__"
                  ".mypy_cache"
                  "generated"
                  "vendor"
                  "examples"
                ]);
            };
            pyproject = true;
            build-system = [ python.pkgs.setuptools ];
            pythonImportsCheck = [ "deb2nix" ];
            nativeCheckInputs = [
              pkgs.dpkg
              pkgs.binutils
              pkgs.gcc
            ];
            makeWrapperArgs = [
              "--prefix PATH : ${runtimePath}"
            ];
            checkPhase = ''
              runHook preCheck
              export PYTHONPATH="$PWD/src:$PYTHONPATH"
              python -m unittest discover -s tests -v
              runHook postCheck
            '';
            meta = {
              description = "Package-agnostic Debian .deb → Nix generator";
              license = pkgs.lib.licenses.mit;
              mainProgram = "deb2nix";
              platforms = pkgs.lib.platforms.linux;
            };
          };
        in
        {
          default = deb2nix;
          inherit deb2nix;
        }
      );

      apps = forAllSystems (system: {
        default = {
          type = "app";
          program = "${self.packages.${system}.deb2nix}/bin/deb2nix";
        };
        deb2nix = self.apps.${system}.default;
      });

      checks = forAllSystems (system: {
        deb2nix = self.packages.${system}.deb2nix;
      });

      devShells = forAllSystems (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
        in
        {
          default = pkgs.mkShell {
            packages = [
              self.packages.${system}.deb2nix
              pkgs.python3
              pkgs.dpkg
              pkgs.binutils
              pkgs.gcc
              pkgs.nix-index
            ];
          };
        }
      );
    };
}
