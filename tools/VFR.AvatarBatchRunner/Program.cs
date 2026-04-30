using System.Collections.Concurrent;
using System.Diagnostics;
using System.Globalization;
using System.Net;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Text.Json.Serialization;

var parseResult = RunnerOptions.Parse(args);
if (parseResult.ShowHelp)
{
    Console.WriteLine(RunnerOptions.HelpText);
    return 0;
}

if (parseResult.Error is not null)
{
    Console.Error.WriteLine(parseResult.Error);
    Console.Error.WriteLine();
    Console.Error.WriteLine(RunnerOptions.HelpText);
    return 2;
}

var runner = new AvatarBatchRunner(parseResult.Options!);
return await runner.RunAsync();

internal sealed class AvatarBatchRunner(RunnerOptions options)
{
    private static readonly JsonSerializerOptions JsonOptions = new(JsonSerializerDefaults.Web)
    {
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
        WriteIndented = true,
        Converters = { new JsonStringEnumConverter() },
    };

    private static readonly JsonSerializerOptions NdjsonOptions = new(JsonSerializerDefaults.Web)
    {
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
        Converters = { new JsonStringEnumConverter() },
    };

    public async Task<int> RunAsync()
    {
        var startedAt = DateTimeOffset.UtcNow;
        var runId = options.RunId;
        var cases = ValidationCaseLoader.Load(options.CasesPath, options.MeasurementMode);

        if (options.CaseNames.Count > 0)
        {
            var wanted = options.CaseNames;
            cases = cases
                .Where(testCase => wanted.Contains(testCase.Name, StringComparer.OrdinalIgnoreCase))
                .ToList();
        }

        if (options.Limit is > 0)
        {
            cases = cases.Take(options.Limit.Value).ToList();
        }

        if (cases.Count == 0)
        {
            Console.Error.WriteLine("No cases selected.");
            return 2;
        }

        Directory.CreateDirectory(options.OutputPath);
        Directory.CreateDirectory(Path.Combine(options.OutputPath, "case-results"));

        var normalizedCasesPath = Path.Combine(options.OutputPath, "cases.normalized.json");
        await WriteJsonAsync(normalizedCasesPath, cases);

        Console.WriteLine($"Avatar batch run: {runId}");
        Console.WriteLine($"Cases: {cases.Count}");
        Console.WriteLine($"Output: {Path.GetFullPath(options.OutputPath)}");

        string? sharedToken = null;
        if (!options.DryRun && options.JwtSigningKey is null && string.IsNullOrWhiteSpace(options.AccessToken))
        {
            sharedToken = await LoginAsync();
        }

        var effectiveConcurrency = options.Concurrency;
        if (!options.DryRun &&
            options.JwtSigningKey is null &&
            effectiveConcurrency > 1)
        {
            Console.WriteLine("Shared-token mode uses one profile; forcing concurrency to 1 to avoid stale tasks.");
            effectiveConcurrency = 1;
        }

        var results = new ConcurrentBag<CaseRunResult>();
        var indexedCases = cases.Select((testCase, index) => (testCase, index)).ToList();
        var stopwatch = Stopwatch.StartNew();

        await Parallel.ForEachAsync(
            indexedCases,
            new ParallelOptions { MaxDegreeOfParallelism = effectiveConcurrency },
            async (item, ct) =>
            {
                var result = options.DryRun
                    ? CaseRunResult.DryRun(item.testCase, item.index, BuildDraftPayload(item.testCase))
                    : await RunCaseAsync(
                        item.testCase,
                        item.index,
                        ResolveTokenForCase(item.testCase, item.index, sharedToken),
                        ct);
                results.Add(result);

                var casePath = Path.Combine(options.OutputPath, "case-results", $"{SafeFileName(item.testCase.Name)}.json");
                await WriteJsonAsync(casePath, result);
                Console.WriteLine($"{item.testCase.Name}: {result.TerminalStatus}");
            });

        stopwatch.Stop();

        var orderedResults = results
            .OrderBy(result => result.Index)
            .ToList();

        await WriteNdjsonAsync(
            Path.Combine(options.OutputPath, "requests.ndjson"),
            orderedResults.SelectMany(result => result.Requests));
        await WriteNdjsonAsync(
            Path.Combine(options.OutputPath, "responses.ndjson"),
            orderedResults.SelectMany(result => result.Responses));

        var summary = BatchSummary.Build(
            runId,
            startedAt,
            DateTimeOffset.UtcNow,
            stopwatch.Elapsed,
            options,
            orderedResults);
        await WriteJsonAsync(Path.Combine(options.OutputPath, "summary.json"), summary);
        await MarkdownReportWriter.WriteAsync(options.ReportPath, summary, orderedResults);

        Console.WriteLine($"Summary: {Path.GetFullPath(Path.Combine(options.OutputPath, "summary.json"))}");
        Console.WriteLine($"Report: {Path.GetFullPath(options.ReportPath)}");

        return orderedResults.Any(result => !IsSuccessfulExitStatus(result.TerminalStatus)) ? 1 : 0;
    }

    private async Task<CaseRunResult> RunCaseAsync(ValidationCase testCase, int index, string accessToken, CancellationToken ct)
    {
        using var caseTimeout = CancellationTokenSource.CreateLinkedTokenSource(ct);
        caseTimeout.CancelAfter(options.CaseTimeout);

        var requests = new List<RequestLogEntry>();
        var responses = new List<ResponseLogEntry>();
        var draftPayload = BuildDraftPayload(testCase);
        var expectedAiRequest = BuildExpectedAiRequest(
            testCase,
            draftPayload,
            JwtFactory.TryReadUserId(accessToken) ?? "<derived-from-jwt>");
        var result = new CaseRunResult(
            Index: index,
            Name: testCase.Name,
            TerminalStatus: "UNKNOWN",
            StartedAt: DateTimeOffset.UtcNow,
            CompletedAt: null,
            Case: testCase,
            DraftPayload: draftPayload,
            ExpectedAiRequest: expectedAiRequest,
            BrokerStart: null,
            TerminalBrokerStatus: null,
            PersistedProfile: null,
            TargetResiduals: new Dictionary<string, ResidualReport>(),
            CaseResiduals: new Dictionary<string, ResidualReport>(),
            Parity: new Dictionary<string, ParityReport>(),
            Requests: requests,
            Responses: responses,
            Error: null);

        try
        {
            using var httpClient = CreateProfileClient(accessToken);

            var upsert = await SendJsonAsync(
                httpClient,
                HttpMethod.Put,
                "/api/v1/profiles/me/studio",
                draftPayload,
                requests,
                responses,
                caseTimeout.Token);
            upsert.EnsureSuccess();

            var start = await SendJsonAsync(
                httpClient,
                HttpMethod.Post,
                "/api/v1/profiles/me/studio/avatar-generation",
                null,
                requests,
                responses,
                caseTimeout.Token);
            start.EnsureSuccess();

            var startPayload = start.Deserialize<StudioAvatarGenerationStartResponse>();
            if (startPayload is null || string.IsNullOrWhiteSpace(startPayload.TaskId))
            {
                return result with
                {
                    TerminalStatus = "FAILURE",
                    CompletedAt = DateTimeOffset.UtcNow,
                    BrokerStart = start.Body,
                    Error = "Broker start response did not include taskId."
                };
            }

            StudioAvatarGenerationStatusResponse? terminalStatus = null;
            JsonNode? terminalRaw = null;
            var pollStopwatch = Stopwatch.StartNew();
            while (pollStopwatch.Elapsed < options.CaseTimeout)
            {
                await Task.Delay(options.PollInterval, caseTimeout.Token);
                var statusExchange = await SendJsonAsync(
                    httpClient,
                    HttpMethod.Get,
                    $"/api/v1/profiles/me/studio/avatar-generation/{Uri.EscapeDataString(startPayload.TaskId)}",
                    null,
                    requests,
                    responses,
                    caseTimeout.Token);
                statusExchange.EnsureSuccess();

                var statusPayload = statusExchange.Deserialize<StudioAvatarGenerationStatusResponse>();
                var normalizedStatus = NormalizeStatus(statusPayload?.Status);
                if (IsTerminalStatus(normalizedStatus))
                {
                    terminalStatus = statusPayload;
                    terminalRaw = statusExchange.Body;
                    break;
                }
            }

            if (terminalStatus is null)
            {
                return result with
                {
                    TerminalStatus = "TIMEOUT",
                    CompletedAt = DateTimeOffset.UtcNow,
                    BrokerStart = start.Body,
                    Error = $"Timed out after {options.CaseTimeout.TotalSeconds:0}s."
                };
            }

            JsonNode? persistedProfile = null;
            if (NormalizeStatus(terminalStatus.Status) == "SUCCESS")
            {
                var profile = await SendJsonAsync(
                    httpClient,
                    HttpMethod.Get,
                    "/api/v1/profiles/me",
                    null,
                    requests,
                    responses,
                    caseTimeout.Token);
                profile.EnsureSuccess();
                persistedProfile = profile.Body;
            }

            var targetResiduals = ResidualCalculator.CompareTargets(
                terminalStatus.Result?.Measurements,
                terminalStatus.Result?.Targets,
                terminalStatus.Result?.MeasurementSources);
            var caseResiduals = ResidualCalculator.CompareCaseTruth(
                terminalStatus.Result?.Measurements,
                testCase.Measurements);
            var parity = ResidualCalculator.ComputeParity(terminalStatus.Result?.Measurements);

            return result with
            {
                TerminalStatus = NormalizeStatus(terminalStatus.Status),
                CompletedAt = DateTimeOffset.UtcNow,
                BrokerStart = start.Body,
                TerminalBrokerStatus = terminalRaw,
                PersistedProfile = persistedProfile,
                TargetResiduals = targetResiduals,
                CaseResiduals = caseResiduals,
                Parity = parity,
            };
        }
        catch (OperationCanceledException)
        {
            return result with
            {
                TerminalStatus = "TIMEOUT",
                CompletedAt = DateTimeOffset.UtcNow,
                Error = $"Timed out after {options.CaseTimeout.TotalSeconds:0}s."
            };
        }
        catch (Exception ex)
        {
            return result with
            {
                TerminalStatus = "FAILURE",
                CompletedAt = DateTimeOffset.UtcNow,
                Error = ex.Message
            };
        }
    }

    private async Task<string> LoginAsync()
    {
        if (string.IsNullOrWhiteSpace(options.Email) || string.IsNullOrWhiteSpace(options.Password))
        {
            throw new InvalidOperationException(
                "Provide --access-token, --jwt-signing-key, or verified-user --email/--password.");
        }

        using var httpClient = new HttpClient { BaseAddress = options.AuthBaseUrl };
        var response = await httpClient.PostAsJsonAsync(
            "/api/v1/sessions",
            new LoginRequest(options.Email, options.Password, AccessTokenLifetime: null),
            JsonOptions);
        var body = await response.Content.ReadAsStringAsync();
        if (!response.IsSuccessStatusCode)
        {
            throw new InvalidOperationException(
                $"Auth login failed with {(int)response.StatusCode} {response.ReasonPhrase}: {body}");
        }

        var node = ParseJsonNode(body);
        var token = node?["data"]?["token"]?["accessToken"]?.GetValue<string>()
            ?? node?["token"]?["accessToken"]?.GetValue<string>();

        return string.IsNullOrWhiteSpace(token)
            ? throw new InvalidOperationException("Auth login response did not include data.token.accessToken.")
            : token;
    }

    private string ResolveTokenForCase(ValidationCase testCase, int index, string? sharedToken)
    {
        if (!string.IsNullOrWhiteSpace(options.AccessToken))
        {
            return options.AccessToken;
        }

        if (!string.IsNullOrWhiteSpace(options.JwtSigningKey))
        {
            var userId = $"{options.JwtUserIdPrefix}-{index + 1:000}-{SafeFileName(testCase.Name)}";
            return JwtFactory.Create(
                userId,
                options.JwtIssuer,
                options.JwtAudience,
                options.JwtSigningKey);
        }

        return sharedToken ?? throw new InvalidOperationException("No access token available.");
    }

    private HttpClient CreateProfileClient(string accessToken)
    {
        var httpClient = new HttpClient { BaseAddress = options.ProfileBaseUrl };
        httpClient.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", accessToken);
        return httpClient;
    }

    private static DraftPayload BuildDraftPayload(ValidationCase testCase)
    {
        var includeMeasurements = testCase.MeasurementMode == MeasurementMode.Explicit;

        return new DraftPayload(
            Height: testCase.HeightCm,
            Weight: testCase.WeightKg,
            BodyType: ToEnumText(testCase.BodyType),
            Gender: ToEnumText(testCase.Gender),
            Muscularity: DefaultMuscularity(testCase.Gender, testCase.BodyType),
            BodyFatPercentage: DefaultBodyFat(testCase.Gender, testCase.BodyType),
            ChestCircumference: includeMeasurements ? testCase.Measurements.GetValueOrDefault("chest_cm") : null,
            WaistCircumference: includeMeasurements ? testCase.Measurements.GetValueOrDefault("waist_cm") : null,
            HipCircumference: includeMeasurements ? testCase.Measurements.GetValueOrDefault("hips_cm") : null,
            ShoulderWidth: includeMeasurements ? testCase.Measurements.GetValueOrDefault("shoulder") : null,
            CalfCircumference: includeMeasurements ? testCase.Measurements.GetValueOrDefault("calf") : null,
            ArmLength: includeMeasurements ? testCase.Measurements.GetValueOrDefault("arm_length_cm") : null,
            TorsoLength: includeMeasurements ? testCase.Measurements.GetValueOrDefault("torso_length") : null,
            LegLength: includeMeasurements ? testCase.Measurements.GetValueOrDefault("leg_length_cm") : null,
            AutoChestCircumference: null,
            AutoWaistCircumference: null,
            AutoHipCircumference: null,
            AutoArmLength: null,
            AutoLegLength: null,
            GeneratedAvatar: null);
    }

    private static ExpectedAiRequest BuildExpectedAiRequest(ValidationCase testCase, DraftPayload draft, string userId) =>
        new(
            UserId: userId,
            Height: draft.Height,
            Weight: draft.Weight,
            BodyType: testCase.BodyType,
            Gender: testCase.Gender,
            Muscularity: draft.Muscularity ?? 0,
            BodyFatPercentage: draft.BodyFatPercentage ?? 0,
            Chest: draft.ChestCircumference ?? 0,
            Waist: draft.WaistCircumference ?? 0,
            Hip: draft.HipCircumference ?? 0,
            Shoulder: draft.ShoulderWidth ?? 0,
            Calf: draft.CalfCircumference ?? 0,
            ArmLength: draft.ArmLength ?? 0,
            TorsoLength: draft.TorsoLength ?? 0,
            LegLength: draft.LegLength ?? 0,
            FaceImageUrl: string.Empty,
            CaptureNote: "Expected request derived from ProfileApi AiEngineClient mapping; black-box runtime cannot observe the actual server-to-server payload.");

    private static bool IsSuccessfulExitStatus(string status) =>
        status is "SUCCESS" or "DRY_RUN";

    private async Task<HttpExchange> SendJsonAsync(
        HttpClient httpClient,
        HttpMethod method,
        string path,
        object? body,
        List<RequestLogEntry> requests,
        List<ResponseLogEntry> responses,
        CancellationToken ct)
    {
        var requestBody = body is null ? null : JsonSerializer.SerializeToNode(body, JsonOptions);
        requests.Add(new RequestLogEntry(
            DateTimeOffset.UtcNow,
            method.Method,
            path,
            requestBody));

        using var request = new HttpRequestMessage(method, path);
        if (body is not null)
        {
            request.Content = JsonContent.Create(body, options: JsonOptions);
        }

        using var response = await httpClient.SendAsync(request, ct);
        var responseBody = await response.Content.ReadAsStringAsync(ct);
        var responseNode = ParseJsonNode(responseBody);

        responses.Add(new ResponseLogEntry(
            DateTimeOffset.UtcNow,
            method.Method,
            path,
            (int)response.StatusCode,
            response.ReasonPhrase ?? string.Empty,
            responseNode,
            string.IsNullOrWhiteSpace(responseBody) ? null : responseBody));

        return new HttpExchange(response.StatusCode, response.ReasonPhrase ?? string.Empty, responseNode, responseBody);
    }

    private static JsonNode? ParseJsonNode(string value)
    {
        if (string.IsNullOrWhiteSpace(value))
        {
            return null;
        }

        try
        {
            return JsonNode.Parse(value);
        }
        catch (JsonException)
        {
            return null;
        }
    }

    private static string NormalizeStatus(string? status) =>
        string.IsNullOrWhiteSpace(status)
            ? "UNKNOWN"
            : status.Trim().ToUpperInvariant();

    private static bool IsTerminalStatus(string status) =>
        status is "SUCCESS" or "FAILURE" or "STALE";

    private static string ToEnumText(string value) =>
        string.IsNullOrWhiteSpace(value)
            ? value
            : char.ToUpperInvariant(value[0]) + value[1..].ToLowerInvariant();

    private static double DefaultMuscularity(string gender, string bodyType) =>
        bodyType.ToLowerInvariant() switch
        {
            "slim" => gender.Equals("female", StringComparison.OrdinalIgnoreCase) ? 32 : 42,
            "athletic" => gender.Equals("female", StringComparison.OrdinalIgnoreCase) ? 58 : 72,
            "curvy" => gender.Equals("female", StringComparison.OrdinalIgnoreCase) ? 30 : 36,
            _ => gender.Equals("female", StringComparison.OrdinalIgnoreCase) ? 44 : 52,
        };

    private static double DefaultBodyFat(string gender, string bodyType) =>
        gender.Equals("female", StringComparison.OrdinalIgnoreCase)
            ? bodyType.ToLowerInvariant() switch
            {
                "slim" => 18,
                "athletic" => 22,
                "curvy" => 34,
                _ => 28,
            }
            : bodyType.ToLowerInvariant() switch
            {
                "slim" => 11,
                "athletic" => 14,
                "curvy" => 26,
                _ => 19,
            };

    private static string SafeFileName(string value)
    {
        var invalid = Path.GetInvalidFileNameChars();
        var builder = new StringBuilder(value.Length);
        foreach (var character in value)
        {
            builder.Append(invalid.Contains(character) ? '_' : character);
        }

        return builder.ToString();
    }

    private static async Task WriteJsonAsync<T>(string path, T value)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(path)!);
        await using var stream = File.Create(path);
        await JsonSerializer.SerializeAsync(stream, value, JsonOptions);
        await stream.WriteAsync(Encoding.UTF8.GetBytes(Environment.NewLine));
    }

    private static async Task WriteNdjsonAsync<T>(string path, IEnumerable<T> values)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(path)!);
        await using var stream = File.Create(path);
        await using var writer = new StreamWriter(stream, new UTF8Encoding(encoderShouldEmitUTF8Identifier: false));
        foreach (var value in values)
        {
            await writer.WriteLineAsync(JsonSerializer.Serialize(value, NdjsonOptions));
        }
    }
}

internal sealed record RunnerOptions(
    string RunId,
    string CasesPath,
    string OutputPath,
    string ReportPath,
    Uri AuthBaseUrl,
    Uri ProfileBaseUrl,
    string? Email,
    string? Password,
    string? AccessToken,
    string? JwtSigningKey,
    string JwtIssuer,
    string JwtAudience,
    string JwtUserIdPrefix,
    int Concurrency,
    TimeSpan PollInterval,
    TimeSpan CaseTimeout,
    int? Limit,
    HashSet<string> CaseNames,
    MeasurementMode MeasurementMode,
    bool DryRun)
{
    public static readonly string HelpText = """
    VFR Avatar Batch Runner

    Usage:
      dotnet run --project tools/VFR.AvatarBatchRunner -- [options]

    Options:
      --cases <path>                  Case JSON file. Default: src/VFR.AiEngine/validation_cases.baseline.json
      --output <path>                 Output directory. Default: tests/artifacts/studio-avatar-batch/<run-id>
      --report <path>                 Markdown report path. Default: agents/reports/avatar-batch-measurement-report.md
      --profile-url <url>             ProfileApi base URL. Default: VFR_BATCH_PROFILE_URL or http://localhost:5288
      --auth-url <url>                Auth base URL. Default: VFR_BATCH_AUTH_URL or http://localhost:1310
      --access-token <token>          Use a pre-issued bearer token.
      --email <email>                 Verified Auth user email for login mode.
      --password <password>           Verified Auth user password for login mode.
      --jwt-signing-key <key>         Generate per-case dev JWTs with this signing key.
      --jwt-issuer <issuer>           JWT issuer. Default: ApplicationAuthAuthServer
      --jwt-audience <audience>       JWT audience. Default: Client
      --jwt-user-id <prefix>          Synthetic user id prefix. Default: avatar-batch
      --measurement-mode <mode>       explicit or profile-only. Default: explicit
      --concurrency <n>               Default: 1. If using shared access token/login, values >1 are forced to 1.
      --poll-interval-seconds <n>     Default: 2
      --case-timeout-seconds <n>      Default: 300
      --limit <n>                     Run only first n selected cases.
      --case <name>                   Include a single case. Can be repeated.
      --dry-run                       Normalize cases and write report without HTTP calls.
      --help                          Show help.
    """;

    public static ParseResult Parse(string[] args)
    {
        var runId = DateTimeOffset.UtcNow.ToString("yyyyMMdd-HHmmss", CultureInfo.InvariantCulture);
        var casesPath = Environment.GetEnvironmentVariable("VFR_BATCH_CASES")
            ?? "src/VFR.AiEngine/validation_cases.baseline.json";
        var outputPath = Environment.GetEnvironmentVariable("VFR_BATCH_OUTPUT")
            ?? Path.Combine("tests", "artifacts", "studio-avatar-batch", runId);
        var reportPath = Environment.GetEnvironmentVariable("VFR_BATCH_REPORT")
            ?? Path.Combine("agents", "reports", "avatar-batch-measurement-report.md");
        var authUrl = Environment.GetEnvironmentVariable("VFR_BATCH_AUTH_URL") ?? "http://localhost:1310";
        var profileUrl = Environment.GetEnvironmentVariable("VFR_BATCH_PROFILE_URL") ?? "http://localhost:5288";
        var email = Environment.GetEnvironmentVariable("VFR_BATCH_EMAIL");
        var password = Environment.GetEnvironmentVariable("VFR_BATCH_PASSWORD");
        var accessToken = Environment.GetEnvironmentVariable("VFR_BATCH_ACCESS_TOKEN");
        var jwtSigningKey = Environment.GetEnvironmentVariable("VFR_BATCH_JWT_SIGNING_KEY");
        var jwtIssuer = Environment.GetEnvironmentVariable("VFR_BATCH_JWT_ISSUER") ?? "ApplicationAuthAuthServer";
        var jwtAudience = Environment.GetEnvironmentVariable("VFR_BATCH_JWT_AUDIENCE") ?? "Client";
        var jwtUserId = Environment.GetEnvironmentVariable("VFR_BATCH_JWT_USER_ID") ?? "avatar-batch";
        var concurrency = 1;
        var pollInterval = TimeSpan.FromSeconds(2);
        var caseTimeout = TimeSpan.FromSeconds(300);
        int? limit = null;
        var dryRun = false;
        var measurementMode = MeasurementMode.Explicit;
        var caseNames = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

        for (var index = 0; index < args.Length; index++)
        {
            var arg = args[index];
            string NextValue()
            {
                if (index + 1 >= args.Length)
                {
                    throw new ArgumentException($"Missing value for {arg}.");
                }

                return args[++index];
            }

            try
            {
                switch (arg)
                {
                    case "--help":
                    case "-h":
                        return new ParseResult(null, ShowHelp: true, Error: null);
                    case "--cases":
                        casesPath = NextValue();
                        break;
                    case "--output":
                        outputPath = NextValue();
                        break;
                    case "--report":
                        reportPath = NextValue();
                        break;
                    case "--auth-url":
                        authUrl = NextValue();
                        break;
                    case "--profile-url":
                        profileUrl = NextValue();
                        break;
                    case "--email":
                        email = NextValue();
                        break;
                    case "--password":
                        password = NextValue();
                        break;
                    case "--access-token":
                        accessToken = NextValue();
                        break;
                    case "--jwt-signing-key":
                        jwtSigningKey = NextValue();
                        break;
                    case "--jwt-issuer":
                        jwtIssuer = NextValue();
                        break;
                    case "--jwt-audience":
                        jwtAudience = NextValue();
                        break;
                    case "--jwt-user-id":
                        jwtUserId = NextValue();
                        break;
                    case "--concurrency":
                        concurrency = ParsePositiveInt(NextValue(), arg);
                        break;
                    case "--poll-interval-seconds":
                        pollInterval = TimeSpan.FromSeconds(ParsePositiveInt(NextValue(), arg));
                        break;
                    case "--case-timeout-seconds":
                        caseTimeout = TimeSpan.FromSeconds(ParsePositiveInt(NextValue(), arg));
                        break;
                    case "--limit":
                        limit = ParsePositiveInt(NextValue(), arg);
                        break;
                    case "--case":
                        caseNames.Add(NextValue());
                        break;
                    case "--measurement-mode":
                        measurementMode = ParseMeasurementMode(NextValue());
                        break;
                    case "--dry-run":
                        dryRun = true;
                        break;
                    default:
                        return new ParseResult(null, ShowHelp: false, Error: $"Unknown argument: {arg}");
                }
            }
            catch (ArgumentException ex)
            {
                return new ParseResult(null, ShowHelp: false, Error: ex.Message);
            }
        }

        if (!Uri.TryCreate(EnsureTrailingSlash(authUrl), UriKind.Absolute, out var authBaseUri))
        {
            return new ParseResult(null, ShowHelp: false, Error: $"Invalid --auth-url: {authUrl}");
        }

        if (!Uri.TryCreate(EnsureTrailingSlash(profileUrl), UriKind.Absolute, out var profileBaseUri))
        {
            return new ParseResult(null, ShowHelp: false, Error: $"Invalid --profile-url: {profileUrl}");
        }

        return new ParseResult(
            new RunnerOptions(
                runId,
                casesPath,
                outputPath,
                reportPath,
                authBaseUri,
                profileBaseUri,
                email,
                password,
                accessToken,
                jwtSigningKey,
                jwtIssuer,
                jwtAudience,
                jwtUserId,
                concurrency,
                pollInterval,
                caseTimeout,
                limit,
                caseNames,
                measurementMode,
                dryRun),
            ShowHelp: false,
            Error: null);
    }

    private static int ParsePositiveInt(string value, string name) =>
        int.TryParse(value, NumberStyles.None, CultureInfo.InvariantCulture, out var parsed) && parsed > 0
            ? parsed
            : throw new ArgumentException($"{name} must be a positive integer.");

    private static MeasurementMode ParseMeasurementMode(string value) =>
        value.Trim().ToLowerInvariant() switch
        {
            "explicit" => MeasurementMode.Explicit,
            "profile-only" => MeasurementMode.ProfileOnly,
            _ => throw new ArgumentException("--measurement-mode must be explicit or profile-only.")
        };

    private static string EnsureTrailingSlash(string value) =>
        value.EndsWith("/", StringComparison.Ordinal) ? value : value + "/";
}

internal sealed record ParseResult(RunnerOptions? Options, bool ShowHelp, string? Error);

internal enum MeasurementMode
{
    Explicit,
    ProfileOnly,
}

internal static class ValidationCaseLoader
{
    public static List<ValidationCase> Load(string casesPath, MeasurementMode measurementMode)
    {
        if (!File.Exists(casesPath))
        {
            throw new FileNotFoundException("Case file not found.", casesPath);
        }

        using var document = JsonDocument.Parse(File.ReadAllText(casesPath));
        var casesElement = document.RootElement.TryGetProperty("cases", out var rootCases)
            ? rootCases
            : document.RootElement;

        if (casesElement.ValueKind != JsonValueKind.Array)
        {
            throw new InvalidOperationException("Case file must contain a root array or a root object with a cases array.");
        }

        var cases = new List<ValidationCase>();
        foreach (var item in casesElement.EnumerateArray())
        {
            var measurements = new Dictionary<string, double>(StringComparer.OrdinalIgnoreCase);
            if (item.TryGetProperty("measurements", out var measurementsElement))
            {
                foreach (var measurement in measurementsElement.EnumerateObject())
                {
                    if (measurement.Value.ValueKind is JsonValueKind.Number &&
                        measurement.Value.TryGetDouble(out var value))
                    {
                        measurements[measurement.Name] = value;
                    }
                }
            }

            cases.Add(new ValidationCase(
                Name: RequiredString(item, "name"),
                Gender: RequiredString(item, "gender").Trim().ToLowerInvariant(),
                HeightCm: RequiredDouble(item, "height_cm"),
                WeightKg: RequiredDouble(item, "weight_kg"),
                BodyType: RequiredString(item, "body_type").Trim().ToLowerInvariant(),
                Measurements: measurements,
                MeasurementMode: measurementMode));
        }

        return cases;
    }

    private static string RequiredString(JsonElement element, string propertyName)
    {
        if (element.TryGetProperty(propertyName, out var property) &&
            property.ValueKind == JsonValueKind.String)
        {
            return property.GetString()!;
        }

        throw new InvalidOperationException($"Case is missing string property '{propertyName}'.");
    }

    private static double RequiredDouble(JsonElement element, string propertyName)
    {
        if (element.TryGetProperty(propertyName, out var property) &&
            property.ValueKind == JsonValueKind.Number &&
            property.TryGetDouble(out var value))
        {
            return value;
        }

        throw new InvalidOperationException($"Case is missing numeric property '{propertyName}'.");
    }
}

internal static class ResidualCalculator
{
    public static Dictionary<string, ResidualReport> CompareTargets(
        IReadOnlyDictionary<string, double>? measurements,
        IReadOnlyDictionary<string, double>? targets,
        IReadOnlyDictionary<string, string>? sources)
    {
        var residuals = new Dictionary<string, ResidualReport>(StringComparer.OrdinalIgnoreCase);
        if (measurements is null || targets is null)
        {
            return residuals;
        }

        foreach (var (name, target) in targets)
        {
            if (!measurements.TryGetValue(name, out var measured))
            {
                continue;
            }

            residuals[name] = BuildResidual(
                name,
                target,
                measured,
                sources?.GetValueOrDefault(name),
                SourceGroup(sources?.GetValueOrDefault(name)));
        }

        return residuals;
    }

    public static Dictionary<string, ResidualReport> CompareCaseTruth(
        IReadOnlyDictionary<string, double>? measurements,
        IReadOnlyDictionary<string, double> caseMeasurements)
    {
        var residuals = new Dictionary<string, ResidualReport>(StringComparer.OrdinalIgnoreCase);
        if (measurements is null)
        {
            return residuals;
        }

        var mapping = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase)
        {
            ["chest_cm"] = "chest_cm",
            ["waist_cm"] = "waist_cm",
            ["hips_cm"] = "hips_cm",
            ["arm_length_cm"] = "arm_length_cm",
            ["leg_length_cm"] = "leg_length_cm",
        };

        foreach (var (caseName, measurementName) in mapping)
        {
            if (caseMeasurements.TryGetValue(caseName, out var target) &&
                measurements.TryGetValue(measurementName, out var measured))
            {
                residuals[measurementName] = BuildResidual(
                    measurementName,
                    target,
                    measured,
                    source: "validation_case",
                    sourceGroup: "case_truth");
            }
        }

        return residuals;
    }

    public static Dictionary<string, ParityReport> ComputeParity(IReadOnlyDictionary<string, double>? measurements)
    {
        var parity = new Dictionary<string, ParityReport>(StringComparer.OrdinalIgnoreCase);
        if (measurements is null)
        {
            return parity;
        }

        AddParity(parity, measurements, "bicep", "left_bicep_cm", "bicep_circumference_cm");
        AddParity(parity, measurements, "thigh", "left_thigh_cm", "thigh_circumference_cm");
        return parity;
    }

    private static void AddParity(
        Dictionary<string, ParityReport> parity,
        IReadOnlyDictionary<string, double> measurements,
        string name,
        string leftKey,
        string proxyKey)
    {
        if (!measurements.TryGetValue(leftKey, out var leftValue) ||
            !measurements.TryGetValue(proxyKey, out var proxyValue))
        {
            return;
        }

        parity[name] = new ParityReport(
            LeftMeasurementKey: leftKey,
            ProxyMeasurementKey: proxyKey,
            LeftValueCm: Round(leftValue),
            ProxyValueCm: Round(proxyValue),
            SignedDifferenceCm: Round(proxyValue - leftValue),
            AbsDifferenceCm: Round(Math.Abs(proxyValue - leftValue)));
    }

    private static ResidualReport BuildResidual(
        string name,
        double target,
        double measured,
        string? source,
        string sourceGroup)
    {
        var signed = measured - target;
        return new ResidualReport(
            Measurement: name,
            Source: source,
            SourceGroup: sourceGroup,
            TargetCm: Round(target),
            MeasuredCm: Round(measured),
            SignedErrorCm: Round(signed),
            AbsErrorCm: Round(Math.Abs(signed)),
            RelativeErrorPct: target == 0 ? null : Round(Math.Abs(signed) / Math.Abs(target) * 100.0));
    }

    private static string SourceGroup(string? source)
    {
        if (string.IsNullOrWhiteSpace(source))
        {
            return "unknown";
        }

        if (source.StartsWith("proxy_targets", StringComparison.OrdinalIgnoreCase))
        {
            return "proxy_targets";
        }

        if (source.Equals("user", StringComparison.OrdinalIgnoreCase))
        {
            return "user";
        }

        if (source.Equals("inferred", StringComparison.OrdinalIgnoreCase))
        {
            return "inferred";
        }

        return source;
    }

    internal static double Round(double value) => Math.Round(value, 4, MidpointRounding.AwayFromZero);
}

internal static class BatchSummary
{
    public static BatchSummaryReport Build(
        string runId,
        DateTimeOffset startedAt,
        DateTimeOffset completedAt,
        TimeSpan duration,
        RunnerOptions options,
        IReadOnlyList<CaseRunResult> results)
    {
        var statusCounts = results
            .GroupBy(result => result.TerminalStatus)
            .OrderBy(group => group.Key)
            .ToDictionary(group => group.Key, group => group.Count());

        var targetResiduals = results
            .SelectMany(result => result.TargetResiduals.Values.Select(residual => (result.Name, Residual: residual)))
            .ToList();

        var caseResiduals = results
            .SelectMany(result => result.CaseResiduals.Values.Select(residual => (result.Name, Residual: residual)))
            .ToList();

        return new BatchSummaryReport(
            RunId: runId,
            DryRun: options.DryRun,
            MeasurementMode: options.MeasurementMode.ToString(),
            StartedAt: startedAt,
            CompletedAt: completedAt,
            DurationSeconds: Math.Round(duration.TotalSeconds, 2),
            CaseCount: results.Count,
            StatusCounts: statusCounts,
            TargetMae: MeanAbs(targetResiduals.Select(item => item.Residual)),
            CaseTruthMae: MeanAbs(caseResiduals.Select(item => item.Residual)),
            SourceGroupMae: targetResiduals
                .GroupBy(item => item.Residual.SourceGroup)
                .OrderBy(group => group.Key)
                .ToDictionary(group => group.Key, group => MeanAbs(group.Select(item => item.Residual))),
            WorstCasesByTargetMae: results
                .Select(result => new WorstCaseSummary(
                    result.Name,
                    result.TerminalStatus,
                    MeanAbs(result.TargetResiduals.Values),
                    MeanAbs(result.CaseResiduals.Values)))
                .OrderByDescending(item => item.TargetMae)
                .ThenByDescending(item => item.CaseTruthMae)
                .Take(10)
                .ToList(),
            WorstMeasurementsByTargetAbsError: targetResiduals
                .OrderByDescending(item => item.Residual.AbsErrorCm)
                .Take(20)
                .Select(item => new WorstMeasurementSummary(
                    item.Name,
                    item.Residual.Measurement,
                    item.Residual.SourceGroup,
                    item.Residual.TargetCm,
                    item.Residual.MeasuredCm,
                    item.Residual.SignedErrorCm,
                    item.Residual.AbsErrorCm,
                    item.Residual.RelativeErrorPct))
                .ToList(),
            Errors: results
                .Where(result => !string.IsNullOrWhiteSpace(result.Error))
                .Select(result => new CaseErrorSummary(result.Name, result.TerminalStatus, result.Error!))
                .ToList());
    }

    private static double? MeanAbs(IEnumerable<ResidualReport> residuals)
    {
        var values = residuals.Select(residual => residual.AbsErrorCm).ToList();
        return values.Count == 0 ? null : ResidualCalculator.Round(values.Average());
    }
}

internal static class MarkdownReportWriter
{
    public static async Task WriteAsync(
        string reportPath,
        BatchSummaryReport summary,
        IReadOnlyList<CaseRunResult> results)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(reportPath)!);
        var builder = new StringBuilder();
        builder.AppendLine("# Avatar Batch Measurement Report");
        builder.AppendLine();
        builder.AppendLine($"- Run ID: `{summary.RunId}`");
        builder.AppendLine($"- Dry run: `{summary.DryRun}`");
        builder.AppendLine($"- Measurement mode: `{summary.MeasurementMode}`");
        builder.AppendLine($"- Cases: `{summary.CaseCount}`");
        builder.AppendLine($"- Duration: `{summary.DurationSeconds.ToString("0.##", CultureInfo.InvariantCulture)}s`");
        builder.AppendLine($"- Target MAE: `{Format(summary.TargetMae)}`");
        builder.AppendLine($"- Case truth MAE: `{Format(summary.CaseTruthMae)}`");
        builder.AppendLine();

        builder.AppendLine("## Status Counts");
        builder.AppendLine();
        foreach (var (status, count) in summary.StatusCounts)
        {
            builder.AppendLine($"- `{status}`: {count}");
        }
        builder.AppendLine();

        builder.AppendLine("## Source Group MAE");
        builder.AppendLine();
        if (summary.SourceGroupMae.Count == 0)
        {
            builder.AppendLine("- No target residuals recorded.");
        }
        else
        {
            foreach (var (source, mae) in summary.SourceGroupMae)
            {
                builder.AppendLine($"- `{source}`: `{Format(mae)}` cm");
            }
        }
        builder.AppendLine();

        builder.AppendLine("## Worst Cases");
        builder.AppendLine();
        foreach (var item in summary.WorstCasesByTargetMae)
        {
            builder.AppendLine($"- `{item.Name}` ({item.Status}): target MAE `{Format(item.TargetMae)}`, case truth MAE `{Format(item.CaseTruthMae)}`");
        }
        builder.AppendLine();

        builder.AppendLine("## Worst Target Residuals");
        builder.AppendLine();
        foreach (var item in summary.WorstMeasurementsByTargetAbsError)
        {
            builder.AppendLine(
                $"- `{item.CaseName}` / `{item.Measurement}` / `{item.SourceGroup}`: target `{item.TargetCm}`, measured `{item.MeasuredCm}`, signed `{item.SignedErrorCm}`, abs `{item.AbsErrorCm}`, rel `{Format(item.RelativeErrorPct)}%`");
        }
        builder.AppendLine();

        var parityRows = results
            .SelectMany(result => result.Parity.Select(item => (CaseName: result.Name, Name: item.Key, item.Value)))
            .ToList();
        builder.AppendLine("## Bicep/Thigh Parity");
        builder.AppendLine();
        if (parityRows.Count == 0)
        {
            builder.AppendLine("- No parity measurements recorded.");
        }
        else
        {
            foreach (var row in parityRows)
            {
                builder.AppendLine($"- `{row.CaseName}` / `{row.Name}`: left `{row.Value.LeftValueCm}`, proxy `{row.Value.ProxyValueCm}`, diff `{row.Value.SignedDifferenceCm}`");
            }
        }
        builder.AppendLine();

        if (summary.Errors.Count > 0)
        {
            builder.AppendLine("## Errors");
            builder.AppendLine();
            foreach (var error in summary.Errors)
            {
                builder.AppendLine($"- `{error.CaseName}` ({error.Status}): {error.Error}");
            }
        }

        await File.WriteAllTextAsync(reportPath, builder.ToString(), new UTF8Encoding(encoderShouldEmitUTF8Identifier: false));
    }

    private static string Format(double? value) =>
        value.HasValue ? value.Value.ToString("0.####", CultureInfo.InvariantCulture) : "n/a";
}

internal static class JwtFactory
{
    public static string Create(string userId, string issuer, string audience, string signingKey)
    {
        var now = DateTimeOffset.UtcNow;
        var header = new Dictionary<string, object>
        {
            ["alg"] = "HS256",
            ["typ"] = "JWT",
        };
        var payload = new Dictionary<string, object>
        {
            ["iss"] = issuer,
            ["aud"] = audience,
            ["sub"] = userId,
            ["http://schemas.xmlsoap.org/ws/2005/05/identity/claims/nameidentifier"] = userId,
            ["name"] = userId,
            ["isRefresh"] = "False",
            ["nbf"] = now.ToUnixTimeSeconds(),
            ["iat"] = now.ToUnixTimeSeconds(),
            ["exp"] = now.AddHours(12).ToUnixTimeSeconds(),
        };

        var headerPart = Base64UrlEncode(JsonSerializer.SerializeToUtf8Bytes(header));
        var payloadPart = Base64UrlEncode(JsonSerializer.SerializeToUtf8Bytes(payload));
        var signingInput = $"{headerPart}.{payloadPart}";
        using var hmac = new HMACSHA256(Encoding.ASCII.GetBytes(signingKey));
        var signature = Base64UrlEncode(hmac.ComputeHash(Encoding.ASCII.GetBytes(signingInput)));
        return $"{signingInput}.{signature}";
    }

    private static string Base64UrlEncode(byte[] bytes) =>
        Convert.ToBase64String(bytes)
            .TrimEnd('=')
            .Replace('+', '-')
            .Replace('/', '_');

    public static string? TryReadUserId(string token)
    {
        var parts = token.Split('.');
        if (parts.Length < 2)
        {
            return null;
        }

        try
        {
            var payloadBytes = Base64UrlDecode(parts[1]);
            using var document = JsonDocument.Parse(payloadBytes);
            var root = document.RootElement;
            return GetString(root, "sub")
                ?? GetString(root, "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/nameidentifier")
                ?? GetString(root, "nameid");
        }
        catch (JsonException)
        {
            return null;
        }
        catch (FormatException)
        {
            return null;
        }
    }

    private static string? GetString(JsonElement element, string propertyName) =>
        element.TryGetProperty(propertyName, out var property) && property.ValueKind == JsonValueKind.String
            ? property.GetString()
            : null;

    private static byte[] Base64UrlDecode(string value)
    {
        var padded = value.Replace('-', '+').Replace('_', '/');
        padded = padded.PadRight(padded.Length + (4 - padded.Length % 4) % 4, '=');
        return Convert.FromBase64String(padded);
    }
}

internal sealed record ValidationCase(
    string Name,
    string Gender,
    double HeightCm,
    double WeightKg,
    string BodyType,
    Dictionary<string, double> Measurements,
    MeasurementMode MeasurementMode);

internal sealed record DraftPayload(
    double Height,
    double Weight,
    string BodyType,
    string Gender,
    double? Muscularity,
    double? BodyFatPercentage,
    double? ChestCircumference,
    double? WaistCircumference,
    double? HipCircumference,
    double? ShoulderWidth,
    double? CalfCircumference,
    double? ArmLength,
    double? TorsoLength,
    double? LegLength,
    double? AutoChestCircumference,
    double? AutoWaistCircumference,
    double? AutoHipCircumference,
    double? AutoArmLength,
    double? AutoLegLength,
    object? GeneratedAvatar);

internal sealed record ExpectedAiRequest(
    [property: JsonPropertyName("user_id")] string UserId,
    [property: JsonPropertyName("height")] double Height,
    [property: JsonPropertyName("weight")] double Weight,
    [property: JsonPropertyName("body_type")] string BodyType,
    [property: JsonPropertyName("gender")] string Gender,
    [property: JsonPropertyName("muscularity")] double Muscularity,
    [property: JsonPropertyName("body_fat_percentage")] double BodyFatPercentage,
    [property: JsonPropertyName("chest")] double Chest,
    [property: JsonPropertyName("waist")] double Waist,
    [property: JsonPropertyName("hip")] double Hip,
    [property: JsonPropertyName("shoulder")] double Shoulder,
    [property: JsonPropertyName("calf")] double Calf,
    [property: JsonPropertyName("arm_length")] double ArmLength,
    [property: JsonPropertyName("torso_length")] double TorsoLength,
    [property: JsonPropertyName("leg_length")] double LegLength,
    [property: JsonPropertyName("face_image_url")] string FaceImageUrl,
    [property: JsonPropertyName("capture_note")] string CaptureNote);

internal sealed record StudioAvatarGenerationStartResponse(
    string? TaskId,
    string? Status,
    string? Message);

internal sealed record StudioAvatarGenerationStatusResponse(
    string? TaskId,
    string? Status,
    int? Progress,
    string? Message,
    StudioAvatarGenerationResultResponse? Result);

internal sealed record StudioAvatarGenerationResultResponse(
    string? ModelUrl,
    Dictionary<string, double>? Measurements,
    Dictionary<string, double>? Targets,
    Dictionary<string, string>? MeasurementSources,
    JsonNode? Profile);

internal sealed record LoginRequest(string Email, string Password, int? AccessTokenLifetime);

internal sealed record RequestLogEntry(
    DateTimeOffset At,
    string Method,
    string Path,
    JsonNode? Body);

internal sealed record ResponseLogEntry(
    DateTimeOffset At,
    string Method,
    string Path,
    int StatusCode,
    string ReasonPhrase,
    JsonNode? Body,
    string? RawBody);

internal sealed record CaseRunResult(
    int Index,
    string Name,
    string TerminalStatus,
    DateTimeOffset StartedAt,
    DateTimeOffset? CompletedAt,
    ValidationCase Case,
    DraftPayload DraftPayload,
    ExpectedAiRequest ExpectedAiRequest,
    JsonNode? BrokerStart,
    JsonNode? TerminalBrokerStatus,
    JsonNode? PersistedProfile,
    Dictionary<string, ResidualReport> TargetResiduals,
    Dictionary<string, ResidualReport> CaseResiduals,
    Dictionary<string, ParityReport> Parity,
    List<RequestLogEntry> Requests,
    List<ResponseLogEntry> Responses,
    string? Error)
{
    public static CaseRunResult DryRun(ValidationCase testCase, int index, DraftPayload draftPayload) =>
        new(
            Index: index,
            Name: testCase.Name,
            TerminalStatus: "DRY_RUN",
            StartedAt: DateTimeOffset.UtcNow,
            CompletedAt: DateTimeOffset.UtcNow,
            Case: testCase,
            DraftPayload: draftPayload,
            ExpectedAiRequest: BuildExpectedDryRun(testCase, draftPayload),
            BrokerStart: null,
            TerminalBrokerStatus: null,
            PersistedProfile: null,
            TargetResiduals: new Dictionary<string, ResidualReport>(),
            CaseResiduals: new Dictionary<string, ResidualReport>(),
            Parity: new Dictionary<string, ParityReport>(),
            Requests:
            [
                new RequestLogEntry(
                    DateTimeOffset.UtcNow,
                    "PUT",
                    "/api/v1/profiles/me/studio",
                    JsonSerializer.SerializeToNode(draftPayload, new JsonSerializerOptions(JsonSerializerDefaults.Web)))
            ],
            Responses: [],
            Error: null);

    private static ExpectedAiRequest BuildExpectedDryRun(ValidationCase testCase, DraftPayload draftPayload) =>
        new(
            UserId: "<derived-from-jwt>",
            Height: draftPayload.Height,
            Weight: draftPayload.Weight,
            BodyType: testCase.BodyType,
            Gender: testCase.Gender,
            Muscularity: draftPayload.Muscularity ?? 0,
            BodyFatPercentage: draftPayload.BodyFatPercentage ?? 0,
            Chest: draftPayload.ChestCircumference ?? 0,
            Waist: draftPayload.WaistCircumference ?? 0,
            Hip: draftPayload.HipCircumference ?? 0,
            Shoulder: draftPayload.ShoulderWidth ?? 0,
            Calf: draftPayload.CalfCircumference ?? 0,
            ArmLength: draftPayload.ArmLength ?? 0,
            TorsoLength: draftPayload.TorsoLength ?? 0,
            LegLength: draftPayload.LegLength ?? 0,
            FaceImageUrl: string.Empty,
            CaptureNote: "Expected request derived from ProfileApi AiEngineClient mapping; dry run does not call services.");
}

internal sealed record ResidualReport(
    string Measurement,
    string? Source,
    string SourceGroup,
    double TargetCm,
    double MeasuredCm,
    double SignedErrorCm,
    double AbsErrorCm,
    double? RelativeErrorPct);

internal sealed record ParityReport(
    string LeftMeasurementKey,
    string ProxyMeasurementKey,
    double LeftValueCm,
    double ProxyValueCm,
    double SignedDifferenceCm,
    double AbsDifferenceCm);

internal sealed record BatchSummaryReport(
    string RunId,
    bool DryRun,
    string MeasurementMode,
    DateTimeOffset StartedAt,
    DateTimeOffset CompletedAt,
    double DurationSeconds,
    int CaseCount,
    Dictionary<string, int> StatusCounts,
    double? TargetMae,
    double? CaseTruthMae,
    Dictionary<string, double?> SourceGroupMae,
    List<WorstCaseSummary> WorstCasesByTargetMae,
    List<WorstMeasurementSummary> WorstMeasurementsByTargetAbsError,
    List<CaseErrorSummary> Errors);

internal sealed record WorstCaseSummary(
    string Name,
    string Status,
    double? TargetMae,
    double? CaseTruthMae);

internal sealed record WorstMeasurementSummary(
    string CaseName,
    string Measurement,
    string SourceGroup,
    double TargetCm,
    double MeasuredCm,
    double SignedErrorCm,
    double AbsErrorCm,
    double? RelativeErrorPct);

internal sealed record CaseErrorSummary(
    string CaseName,
    string Status,
    string Error);

internal sealed record HttpExchange(
    HttpStatusCode StatusCode,
    string ReasonPhrase,
    JsonNode? Body,
    string RawBody)
{
    public void EnsureSuccess()
    {
        if ((int)StatusCode is < 200 or > 299)
        {
            throw new InvalidOperationException($"HTTP {(int)StatusCode} {ReasonPhrase}: {RawBody}");
        }
    }

    public T? Deserialize<T>() =>
        string.IsNullOrWhiteSpace(RawBody)
            ? default
            : JsonSerializer.Deserialize<T>(RawBody, new JsonSerializerOptions(JsonSerializerDefaults.Web));
}
