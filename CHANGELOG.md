# Changelog

## Unreleased

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

## 1.0.0

Initial release
