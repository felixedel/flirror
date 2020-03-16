# Changelog

## [Unreleased]

### Deprecated
- Change the config key `modules.type` to `modules.module`. This key is used to
  specify which module should be used for this element in the configuration
  file. Renaming this key makes it more clear that one should specify the
  module's name there and not some mysterious "type". The old version is still
  supported, but will be removed in future versions.

## [v1.0.1] - 2020-02-28

### Notes
- Automated docker builds on [Docker Hub](https://hub.docker.com/) were set up.
  Thus, you can now simply deploy flirror via its
  [docker image](https://hub.docker.com/r/felixedel/flirror).
  The tag `latest` always contains the latest master state. For each release a
  dedicated tag with the release version will be available (e.g. `1.0.0`).

  Docker builds for Raspberry Pi are not automated yet as they must be built on
  armv7 architecture which is not supported by Docker Hub. Thus, they are built
  manually on a Raspberry Pi for now. There will be docker images available for
  each release, although I'm not sure if I will follow up on the master
  until these builds are automated. The resulting docker images will be tagged
  as `latest-armv7`, or for a release e.g. `1.0.0-armv7`.

### Fixes
- Added missing gunicorn depedency.

## [v1.0.0] - 2020-02-25

Initial release

[Unreleased]: https://github.com/felixedel/flirror/compare/v1.0.1...HEAD
[v1.0.1]: https://github.com/felixedel/flirror/compare/v1.0.0...v1.0.1
[v1.0.0]: https://github.com/felixedel/flirror/releases/tag/v1.0.0
