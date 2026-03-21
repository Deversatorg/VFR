# ApplicationAuth.Domain Context

Updated: 2026-03-21

## Role

Domain entities and enums for the auth slice.

## Important note

- The `Profile` entity in this project is auth-side domain data.
- It is not the same thing as the separate `VFR.ProfileApi` service and its database.

## Important files

- `Entities/Identity/*`
- `Entities/Telegram/*`
- `Enums/*`

## Current issues

- This domain surface spans users, plans, subscriptions, verification, and Telegram concerns.
- That breadth makes seemingly small entity changes expensive.
- The project is now a simpler SDK-style net8 project, but entity changes here still fan out into DAL, auth startup, and Telegram handlers quickly.
- Keep cross-service naming clear so auth-side profile concepts do not get confused with `VFR.ProfileApi`.

## Open next

- `Entities/Identity/IdentityUser.cs`
- `Entities/Identity/Plan.cs`
- `Enums/SubscriptionStatus.cs`
