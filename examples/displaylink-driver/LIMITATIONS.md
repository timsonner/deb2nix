# LIMITATIONS — `displaylink-driver` (driver)

**Success criterion (Phase 1/3 prep):** honest stub + this report. A full
DisplayLink *runtime* needs EVDI/DKMS on NixOS; that is **not** done here.

## Policy

- Tim approval 2026-09-10 accepted the Synaptics/DisplayLink EULA and unfree.
- deb2nix still **must not** `insmod`, run DKMS, load `evdi`, or change Tim's machines.
- Analysis + generate + `nix build` of *userland* expressions only.
- Do not publish this expression to public nixpkgs.

## Classifier evidence

- name/description matches driver token 'displaylink'
- name/description matches driver token 'evdi'
- name/description matches driver token 'dkms'

Hash: `sha256-zHVC+5aQb5cPwTVO2DwKhRVH96RoCa2zNlmKDjGxWKM=`
Depends: `libc6 (>= 2.34), libgcc-s1 (>= 3.0), libstdc++6 (>= 9), libusb-1.0-0 (>= 2:1.0.23~), libuuid1 (>= 2.16), evdi-dkms (>= 1.12.0) | evdi (>= 1.12.0), libevdi1 (>= 1.12.0) | evdi (>= 1.12.0)`

## What nixpkgs already has

- `hardware.video.displaylink` (NixOS module)
- `evdi` kernel package
- Often `requireFile` + unfree for the vendor blob

See `nixos-module.stub.nix` (commented; not enabled).

## What this generate step produced

- `package.nix` **throws** — will not unpack into a fake "it works" FHS env.
- `LIMITATIONS.md` (this file)
- `nixos-module.stub.nix` — documentation only

If userspace binaries exist in the `.deb` (DisplayLinkManager, udev rules),
they are useless without the kernel module. Patchelf-only userland is not
claimed as a working driver.
