# Downstream fork notes

This repository is the `KAITO9999/codex-vl` downstream fork of
[`DioNanos/codex-vl`](https://github.com/DioNanos/codex-vl), which itself
extends [OpenAI Codex](https://github.com/openai/codex).

## Source baseline

- OpenAI Codex stable baseline: `rust-v0.172.0`.
- Original VL base: `0.166.0-vl.2` / `rust-v0.166.0`.
- Fork target version: `0.172.0-vl.1` (unreleased candidate).
- Current integration branch: `sync/openai-rust-v0.172.0` (default branch is not promoted yet).
- Fork-owned release, update, installer, and issue endpoints target
  `KAITO9999/codex-vl`.

## Preserved upstream assets

The V8 prebuilt artifact URLs intentionally continue to use
`DioNanos/codex-vl` release assets. They are shared upstream build artifacts,
not this fork's application release feed. The upstream announcement tip also
remains sourced from the original project until this fork maintains its own.

## Packaging status

The npm package name and platform package scopes (`@mmmbuto/codex-vl*`) are
inherited from the upstream VL project. This fork does not own that npm scope
and has not published a current package. Do not publish from this fork under
the inherited scope. A future public npm release requires an owned package
namespace and matching launcher/update tests.

The published upstream `latest` and `next` channels still refer to
`0.166.0-vl.2`. This fork's `0.172.0-vl.1` source target is not published yet.
