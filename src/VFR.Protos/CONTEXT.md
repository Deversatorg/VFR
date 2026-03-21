# VFR.Protos Context

Updated: 2026-03-20

## Role

Shared .NET gRPC client contract project generated from `protos/avatar.proto`.

## What it contains

- Generated client-side C# stubs for the avatar service contract
- The project itself does not contain business logic

## Important files

- `VFR.Protos.csproj`
- `../../protos/avatar.proto`

## Current state

- Code search on 2026-03-20 did not find active references from the running .NET services.
- That means this project is either future-facing or a leftover from an older integration path.

## Current issues

- If the HTTP path remains primary, this project can drift or become dead weight.
- If a .NET-to-AI gRPC path is reintroduced, this is the first place to verify before changing anything else.

## Open next

- `VFR.Protos.csproj`
- `../../protos/avatar.proto`
