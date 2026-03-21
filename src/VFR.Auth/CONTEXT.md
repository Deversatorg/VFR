# VFR.Auth Slice Context

Updated: 2026-03-21

## Role

This folder contains the auth and billing slice. It is older and broader than the other services, and it is still on .NET 8.

## Projects in this slice

- `ApplicationAuth`: web API and startup
- `ApplicationAuth.Common`: shared constants, helpers, exceptions
- `ApplicationAuth.DAL`: EF Core data access and migrations
- `ApplicationAuth.Domain`: entities and enums
- `ApplicationAuth.ResourceLibrary`: localized resources
- `ApplicationAuth.ServiceDefaults`: net8 service-default helpers

## What this slice owns

- registration, login, refresh, logout
- admin flows
- verification and password recovery
- billing and Stripe-related endpoints
- Telegram-related flows

## Current issues

- This slice is larger and more template-derived than the rest of the repo.
- It duplicates the service-defaults idea instead of sharing the net9 version.
- The auth test harness is green again, but it depends on explicit `Testing`-environment startup behavior for JWT configuration.
- The slice still mixes modern ASP.NET patterns with older project history, but the DAL cleanup removed some legacy artifacts such as `packages.config`.

## Open next

- `ApplicationAuth/CONTEXT.md`
- `ApplicationAuth.DAL/CONTEXT.md`
- `README.md`
