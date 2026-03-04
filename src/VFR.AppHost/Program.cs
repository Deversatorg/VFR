var builder = DistributedApplication.CreateBuilder(args);

// ──────────────────────────────────────────────────────────────────
// Infrastructure
// ──────────────────────────────────────────────────────────────────
var postgres = builder.AddPostgres("vfr-db")
    .WithPgAdmin();

var authDb    = postgres.AddDatabase("auth");
var profileDb = postgres.AddDatabase("profiles");

var redis = builder.AddRedis("vfr-cache");

// Python gRPC AI Engine (built from src/VFR.AiEngine/Dockerfile)
// Aspire builds the Docker image automatically; ProfileApi discovers it via env var.
var aiEngine = builder.AddDockerfile("vfr-aiengine", "../VFR.AiEngine")
    .WithHttpEndpoint(port: 50051, targetPort: 50051, name: "grpc", isProxied: false); 
    // .WithHttpEndpoint defaults to http scheme. 
    // In dev, Aspire might try to proxy this over https if not careful.

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
    .WaitFor(authService)
    .WaitFor(profileApi)
    .WithEnvironment("VITE_AUTH_API_URL", authService.GetEndpoint("http"))
    .WithEnvironment("VITE_PROFILE_API_URL", profileApi.GetEndpoint("http"))
    .WithHttpEndpoint(env: "PORT")
    .WithExternalHttpEndpoints()
    .PublishAsDockerFile();

builder.Build().Run();
