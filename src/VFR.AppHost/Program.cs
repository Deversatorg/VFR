var builder = DistributedApplication.CreateBuilder(args);

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
    // PyTorch deadlock prevention
    .WithEnvironment("OMP_NUM_THREADS", "1")
    .WithHttpEndpoint(port: 50051, targetPort: 50051, name: "grpc", isProxied: false)
    .WithHttpEndpoint(port: 8000, targetPort: 8000, name: "http"); 

// Python Celery Worker (using the same Dockerfile)
var aiEngineWorker = builder.AddDockerfile("vfr-aiengine-worker", "../VFR.AiEngine")
    .WithReference(redis)
    .WithBindMount("../avatars_storage", "/app/avatars")
    // Hot-reload: same code mounts as the FastAPI container
    .WithBindMount("../VFR.AiEngine/ml_pipeline.py",      "/app/ml_pipeline.py")
    .WithBindMount("../VFR.AiEngine/worker.py",           "/app/worker.py")
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
    // PyTorch deadlock prevention
    .WithEnvironment("OMP_NUM_THREADS", "1")
    .WithArgs("celery", "-A", "worker.celery_app", "worker", "--loglevel=info", "--pool=solo");

// ──────────────────────────────────────────────────────────────────
// Microservices
// ──────────────────────────────────────────────────────────────────
var authService = builder.AddProject<Projects.ApplicationAuth>("vfr-auth")
    .WithReference(authDb)
    .WithEnvironment("ConnectionStrings__Connection", authDb)
    .WaitFor(authDb);

var profileApi = builder.AddProject<Projects.VFR_ProfileApi>("vfr-profileapi")
    .WithReference(profileDb)
    .WithReference(redis)
    .WithReference(authService)   // JWT validation service discovery
    .WithReference(aiEngine.GetEndpoint("grpc")) // Inject AI Engine grpc endpoint
    .WaitFor(profileDb)
    .WaitFor(redis)
    .WaitFor(aiEngine)
    .WaitFor(authService);

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
    .WithHttpEndpoint(env: "PORT")
    .WithExternalHttpEndpoints()
    .PublishAsDockerFile();

builder.Build().Run();
