# Changelog

## [0.6.1](https://github.com/DArtagan/bookdrop/compare/v0.6.0...v0.6.1) (2026-11-07)


### Bug Fixes

* give the Shortcut the confirmation page's full URL ([#25](https://github.com/DArtagan/bookdrop/issues/25)) ([56e095b](https://github.com/DArtagan/bookdrop/commit/56e095bb0072bc48f9da0a2c9c166cecb5543f47))

## [0.6.0](https://github.com/DArtagan/bookdrop/compare/v0.5.0...v0.6.0) (2026-11-07)


### Features

* share to bookdrop from an iPhone through a Shortcut ([#23](https://github.com/DArtagan/bookdrop/issues/23)) ([94d0b00](https://github.com/DArtagan/bookdrop/commit/94d0b0085c32731a0dadbbbeeaacaee9c839b443))


### Documentation

* log remove-dry-run and record that bookdrop needs no login ([#22](https://github.com/DArtagan/bookdrop/issues/22)) ([7942b00](https://github.com/DArtagan/bookdrop/commit/7942b00cbdb16043df07503cb5e82069c93d4bdb))

## [0.5.0](https://github.com/DArtagan/bookdrop/compare/v0.4.0...v0.5.0) (2026-11-07)


### ⚠ BREAKING CHANGES

* BOOKDROP_DRY_RUN no longer exists, and bookdrop writes into the books root whenever a book is confirmed. The example compose.yaml mounts it writable.

### Features

* remove dry run ([#20](https://github.com/DArtagan/bookdrop/issues/20)) ([d5ca204](https://github.com/DArtagan/bookdrop/commit/d5ca204f9643e7c7c58230ecb9d1ea412f005a86))

## [0.4.0](https://github.com/DArtagan/bookdrop/compare/v0.3.1...v0.4.0) (2026-11-05)


### Features

* file confirmed books into the library and ask Stump to scan ([#17](https://github.com/DArtagan/bookdrop/issues/17)) ([85725d5](https://github.com/DArtagan/bookdrop/commit/85725d5ac4bec2197d9ee1f82a5f90d58667320f))

## [0.3.1](https://github.com/DArtagan/bookdrop/compare/v0.3.0...v0.3.1) (2026-11-05)


### Bug Fixes

* show and log a failed Open Library lookup, and let it be retried ([#14](https://github.com/DArtagan/bookdrop/issues/14)) ([6bb1a5d](https://github.com/DArtagan/bookdrop/commit/6bb1a5d0e8910b0215e9693808b8d5c08a5c324f))

## [0.3.0](https://github.com/DArtagan/bookdrop/compare/v0.2.2...v0.3.0) (2026-11-05)


### Features

* confirm a dropped book's metadata before filing ([#13](https://github.com/DArtagan/bookdrop/issues/13)) ([8fbad67](https://github.com/DArtagan/bookdrop/commit/8fbad67fd35fb5931b11151383eacca95b3d46e3))


### Documentation

* let a pull request's title decide how it is merged ([#11](https://github.com/DArtagan/bookdrop/issues/11)) ([9d32ace](https://github.com/DArtagan/bookdrop/commit/9d32ace7e1ff6acda3b41c2e07e583e296995eb6))

## [0.2.2](https://github.com/DArtagan/bookdrop/compare/v0.2.1...v0.2.2) (2026-11-03)


### Bug Fixes

* report the dropped book by its title and what was done to it ([369515e](https://github.com/DArtagan/bookdrop/commit/369515eca7e946ac96e51d50ad681d75b1ac0afb))

## [0.2.1](https://github.com/DArtagan/bookdrop/compare/v0.2.0...v0.2.1) (2026-11-03)


### Bug Fixes

* let iOS pick an .acsm in the upload form ([#7](https://github.com/DArtagan/bookdrop/issues/7)) ([842fa43](https://github.com/DArtagan/bookdrop/commit/842fa430a91be5c4e3913c47197c4f22d1627262))

## [0.2.0](https://github.com/DArtagan/bookdrop/compare/v0.1.0...v0.2.0) (2026-11-03)


### Features

* fulfil and strip Adobe DRM from dropped books ([7e7b2f3](https://github.com/DArtagan/bookdrop/commit/7e7b2f3556a573d90782ce1a58e085f8e901c392))
* fulfil and strip Adobe DRM from dropped books ([#5](https://github.com/DArtagan/bookdrop/issues/5)) ([fc0bebd](https://github.com/DArtagan/bookdrop/commit/fc0bebd6ff2a7e81e81d3a59748dffc46b625625))


### Documentation

* record the ByteBooks identity and the first Kobo book ([#2](https://github.com/DArtagan/bookdrop/issues/2)) ([3597210](https://github.com/DArtagan/bookdrop/commit/35972102b07f6402fb3787a9a9baf408182125f2))

## 0.1.0 (2026-11-03)


### Features

* scaffold bookdrop ([4eb324b](https://github.com/DArtagan/bookdrop/commit/4eb324befcabd9d2cb16fc2d01fdf1c711587c69))
