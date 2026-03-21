# ApplicationAuth.Common Context

Updated: 2026-03-21

## Role

Shared constants, validation attributes, exceptions, and helper extensions used across the auth slice.

## Important files

- `Constants/AuthOptions.cs`
- `Constants/ResponseMessages.cs`
- `Exceptions/CustomException.cs`
- `Attributes/*`
- `Extensions/*`

## Current issues

- This kind of project easily turns into a catch-all helper bucket.
- Small changes here can ripple through all auth projects.
- `AuthOptions` now carries the canonical issuer/audience defaults plus shared signing-key helpers, so JWT changes here affect both startup and token issuance.
- Keep it free from infrastructure and IO concerns.

## Open next

- `Constants/AuthOptions.cs`
- `Exceptions/CustomException.cs`
