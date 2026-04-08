using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Hosting;

var builder = DistributedApplication.CreateBuilder(args);
using var bootstrapLoggerFactory = LoggerFactory.Create(logging =>
{
    logging.ClearProviders();
    logging.AddSimpleConsole(options =>
    {
        options.TimestampFormat = "O ";
        options.SingleLine = true;
    });
});
var bootstrapLogger = bootstrapLoggerFactory.CreateLogger("VFR.AppHost");
var deploymentEnvironment = builder.Environment.EnvironmentName;
var telemetryNamespace = builder.Configuration["OTEL_SERVICE_NAMESPACE"]?.Trim() ?? "virtual-fitting-room";
var otlpEndpoint = builder.Configuration["OTEL_EXPORTER_OTLP_ENDPOINT"]?.Trim();
var enableAuthStartupBootstrap = builder.Environment.IsDevelopment();

var jwtIssuer = builder.Configuration["Jwt:Issuer"] ?? "ApplicationAuthAuthServer";
var jwtAudience = builder.Configuration["Jwt:Audience"] ?? "Client";
var jwtSigningKey = builder.Configuration["Jwt:SigningKey"];
var bootstrapAdminEmail = builder.Configuration["BootstrapAdmin:Email"] ?? "admin@test.com";
var bootstrapAdminPassword = builder.Configuration["BootstrapAdmin:Password"] ?? "Welcome1!";
if (string.IsNullOrWhiteSpace(jwtSigningKey))
{
    jwtSigningKey = Convert.ToBase64String(System.Security.Cryptography.RandomNumberGenerator.GetBytes(64));
    bootstrapLogger.LogWarning("Jwt:SigningKey was not configured. Generated an ephemeral development signing key.");
}

// ──────────────────────────────────────────────────────────────────
// Infrastructure
// ──────────────────────────────────────────────────────────────────
var postgres = builder.AddPostgres("vfr-db")
    .WithPgAdmin();

var authDb    = postgres.AddDatabase("auth");
var profileDb = postgres.AddDatabase("profiles");

var redis = builder.AddRedis("vfr-cache");

// Python AI Engine (gRPC + FastAPI)
// Aspire builds the Docker image automatically; ProfileApi discovers it via env var.
var aiEngine = builder.AddDockerfile("vfr-aiengine", "../VFR.AiEngine")
    .WithReference(redis)
    .WithBindMount("../avatars_storage", "/app/avatars")
    // Hot-reload: mount Python source files directly so changes apply without rebuild
    .WithBindMount("../VFR.AiEngine/ml_pipeline.py",      "/app/ml_pipeline.py")
    .WithBindMount("../VFR.AiEngine/main.py",             "/app/main.py")
    .WithBindMount("../VFR.AiEngine/worker.py",           "/app/worker.py")
    .WithBindMount("../VFR.AiEngine/logging_config.py",   "/app/logging_config.py")
    .WithBindMount("../VFR.AiEngine/garment_pipeline.py", "/app/garment_pipeline.py")
    .WithBindMount("../VFR.AiEngine/s3_client.py",        "/app/s3_client.py")
    .WithBindMount("../VFR.AiEngine/anthropometry.py",    "/app/anthropometry.py")
    .WithBindMount("../VFR.AiEngine/measurement_optimizer.py", "/app/measurement_optimizer.py")
    .WithBindMount("../VFR.AiEngine/extract_vertex_loops.py", "/app/extract_vertex_loops.py")
    .WithEnvironment("REDIS_URL", redis.GetEndpoint("tcp"))
    // Backblaze B2 / S3-compatible storage credentials
    .WithEnvironment("S3_ENDPOINT_URL", builder.Configuration["S3_ENDPOINT_URL"] ?? "")
    .WithEnvironment("S3_ACCESS_KEY",   builder.Configuration["S3_ACCESS_KEY"]   ?? "")
    .WithEnvironment("S3_SECRET_KEY",   builder.Configuration["S3_SECRET_KEY"]   ?? "")
    .WithEnvironment("S3_BUCKET_NAME",  builder.Configuration["S3_BUCKET_NAME"]  ?? "vfr-3d-assets")
    .WithEnvironment("DEPLOYMENT_ENVIRONMENT", deploymentEnvironment)
    .WithEnvironment("OTEL_SERVICE_NAME", "vfr-aiengine")
    .WithEnvironment("OTEL_SERVICE_NAMESPACE", telemetryNamespace)
    // PyTorch deadlock prevention
    .WithEnvironment("OMP_NUM_THREADS", "1")
    .WithHttpEndpoint(port: 50051, targetPort: 50051, name: "grpc", isProxied: false)
    .WithHttpEndpoint(port: 8000, targetPort: 8000, name: "http"); 

if (!string.IsNullOrWhiteSpace(otlpEndpoint))
{
    aiEngine.WithEnvironment("OTEL_EXPORTER_OTLP_ENDPOINT", otlpEndpoint);
}

// Python Celery Worker (using the same Dockerfile)
var aiEngineWorker = builder.AddDockerfile("vfr-aiengine-worker", "../VFR.AiEngine")
    .WithReference(redis)
    .WithBindMount("../avatars_storage", "/app/avatars")
    // Hot-reload: same code mounts as the FastAPI container
    .WithBindMount("../VFR.AiEngine/ml_pipeline.py",      "/app/ml_pipeline.py")
    .WithBindMount("../VFR.AiEngine/worker.py",           "/app/worker.py")
    .WithBindMount("../VFR.AiEngine/logging_config.py",   "/app/logging_config.py")
    .WithBindMount("../VFR.AiEngine/garment_pipeline.py", "/app/garment_pipeline.py")
    .WithBindMount("../VFR.AiEngine/s3_client.py",        "/app/s3_client.py")
    .WithBindMount("../VFR.AiEngine/anthropometry.py",    "/app/anthropometry.py")
    .WithBindMount("../VFR.AiEngine/measurement_optimizer.py", "/app/measurement_optimizer.py")
    .WithBindMount("../VFR.AiEngine/extract_vertex_loops.py", "/app/extract_vertex_loops.py")
    .WithEnvironment("REDIS_URL", redis.GetEndpoint("tcp"))
    // Backblaze B2 / S3-compatible storage credentials (same as FastAPI container)
    .WithEnvironment("S3_ENDPOINT_URL", builder.Configuration["S3_ENDPOINT_URL"] ?? "")
    .WithEnvironment("S3_ACCESS_KEY",   builder.Configuration["S3_ACCESS_KEY"]   ?? "")
    .WithEnvironment("S3_SECRET_KEY",   builder.Configuration["S3_SECRET_KEY"]   ?? "")
    .WithEnvironment("S3_BUCKET_NAME",  builder.Configuration["S3_BUCKET_NAME"]  ?? "vfr-3d-assets")
    .WithEnvironment("DEPLOYMENT_ENVIRONMENT", deploymentEnvironment)
    .WithEnvironment("OTEL_SERVICE_NAME", "vfr-aiengine-worker")
    .WithEnvironment("OTEL_SERVICE_NAMESPACE", telemetryNamespace)
    // PyTorch deadlock prevention
    .WithEnvironment("OMP_NUM_THREADS", "1")
    .WithArgs("celery", "-A", "worker.celery_app", "worker", "--loglevel=info", "--pool=solo");

if (!string.IsNullOrWhiteSpace(otlpEndpoint))
{
    aiEngineWorker.WithEnvironment("OTEL_EXPORTER_OTLP_ENDPOINT", otlpEndpoint);
}

// ──────────────────────────────────────────────────────────────────
// Microservices
// ──────────────────────────────────────────────────────────────────
var authService = builder.AddProject<Projects.ApplicationAuth>("vfr-auth")
    .WithReference(authDb)
    .WithEnvironment("ConnectionStrings__Connection", authDb)
    .WithEnvironment("ASPNETCORE_ENVIRONMENT", deploymentEnvironment)
    .WithEnvironment("DOTNET_ENVIRONMENT", deploymentEnvironment)
    .WithEnvironment("Jwt__Issuer", jwtIssuer)
    .WithEnvironment("Jwt__Audience", jwtAudience)
    .WithEnvironment("Jwt__SigningKey", jwtSigningKey)
    .WithEnvironment("DEPLOYMENT_ENVIRONMENT", deploymentEnvironment)
    .WithEnvironment("OTEL_SERVICE_NAME", "vfr-auth")
    .WithEnvironment("OTEL_SERVICE_NAMESPACE", telemetryNamespace)
    .WithEnvironment("BootstrapAdmin__Email", bootstrapAdminEmail)
    .WithEnvironment("BootstrapAdmin__Password", bootstrapAdminPassword)
    .WaitFor(authDb);

if (enableAuthStartupBootstrap)
{
    authService.WithEnvironment("VFR_ENABLE_STARTUP_DB_BOOTSTRAP", "true");
}

if (!string.IsNullOrWhiteSpace(otlpEndpoint))
{
    authService.WithEnvironment("OTEL_EXPORTER_OTLP_ENDPOINT", otlpEndpoint);
}

var profileApi = builder.AddProject<Projects.VFR_ProfileApi>("vfr-profileapi")
    .WithReference(profileDb)
    .WithReference(redis)
    .WithReference(authService)   // JWT validation service discovery
    .WithEnvironment("ASPNETCORE_ENVIRONMENT", deploymentEnvironment)
    .WithEnvironment("DOTNET_ENVIRONMENT", deploymentEnvironment)
    .WithEnvironment("Jwt__Issuer", jwtIssuer)
    .WithEnvironment("Jwt__Audience", jwtAudience)
    .WithEnvironment("Jwt__SigningKey", jwtSigningKey)
    .WithEnvironment("DEPLOYMENT_ENVIRONMENT", deploymentEnvironment)
    .WithEnvironment("OTEL_SERVICE_NAME", "vfr-profileapi")
    .WithEnvironment("OTEL_SERVICE_NAMESPACE", telemetryNamespace)
    .WaitFor(profileDb)
    .WaitFor(redis)
    .WaitFor(authService);

if (!string.IsNullOrWhiteSpace(otlpEndpoint))
{
    profileApi.WithEnvironment("OTEL_EXPORTER_OTLP_ENDPOINT", otlpEndpoint);
}

var vfrWeb = builder.AddNpmApp("vfr-web", "../vfr-web", "dev")
    .WithReference(authService)
    .WithReference(profileApi)
    .WithReference(aiEngine.GetEndpoint("http"))
    .WaitFor(authService)
    .WaitFor(profileApi)
    .WaitFor(aiEngine)
    .WithEnvironment("VITE_AUTH_API_URL", authService.GetEndpoint("http"))
    .WithEnvironment("VITE_PROFILE_API_URL", profileApi.GetEndpoint("http"))
    .WithEnvironment("VITE_AI_ENGINE_API_URL", aiEngine.GetEndpoint("http"))
    .WithEnvironment("VITE_APP_ENVIRONMENT", deploymentEnvironment)
    .WithHttpEndpoint(env: "PORT")
    .WithExternalHttpEndpoints()
    .PublishAsDockerFile();

authService.WithEnvironment("Cors__AllowedOrigins__0", vfrWeb.GetEndpoint("http"));
profileApi.WithEnvironment("Cors__AllowedOrigins__0", vfrWeb.GetEndpoint("http"));

builder.Build().Run();
