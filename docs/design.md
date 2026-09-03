# Design

## Release process

The `Release` workflow (`.github/workflows/release.yml`) reconciles the
version already committed on `main` into a complete, verifiable GitHub
Release. A normal merge to `main` is the release trigger: maintainers never
create or push tags by hand, and the workflow never runs from a pull request
build. Reruns are safe; an already-published version is left immutable.

SWIS is a tree-installed HACS integration (no `zip_release` archive), so the
release job creates the tag and the GitHub Release directly from the tagged
tree. It skips the archive, SBOM, checksum, and attestation steps that a
`zip_release` repository (one that ships a built archive as a release asset)
would need, since HACS installs this integration straight from the tagged
source tree.
