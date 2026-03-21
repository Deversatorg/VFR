# ApplicationAuth.ResourceLibrary Context

Updated: 2026-03-20

## Role

Localized resource strings for the auth slice, mainly errors and validation messages.

## Important files

- `ErrorsResource.cs`
- `Resources/ErrorsResource.en.resx`
- `Resources/ErrorsResource.ru.resx`

## Current issues

- Resource keys must stay aligned with exceptions and validators.
- It is easy for one language file to drift from the other.
- Changes here are low-risk technically but high-visibility for user-facing behavior.

## Open next

- `ErrorsResource.cs`
- `Resources/ErrorsResource.en.resx`
- `Resources/ErrorsResource.ru.resx`
