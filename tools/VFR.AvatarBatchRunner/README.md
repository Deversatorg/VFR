# VFR Avatar Batch Runner

Controlled runtime measurement harness for `Studio -> ProfileApi -> AiEngine`.

## Dry Run

```powershell
dotnet run --project tools/VFR.AvatarBatchRunner -- --dry-run
```

## Runtime Run

Point the runner at a running AppHost/ProfileApi and provide either a token,
login credentials for a verified user, or a JWT signing key that matches
ProfileApi configuration.

```powershell
dotnet run --project tools/VFR.AvatarBatchRunner -- `
  --cases src/VFR.AiEngine/validation_cases.baseline.json `
  --output tests/artifacts/studio-avatar-batch/manual-run `
  --profile-url http://localhost:5288 `
  --jwt-signing-key integration-tests-signing-key-1234567890
```

Use `--measurement-mode profile-only` to test pure inferred/profile generation.
The default `explicit` mode sends case measurements as manual Studio inputs.
