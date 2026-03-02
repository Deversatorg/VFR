using FluentValidation;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.EntityFrameworkCore;
using Microsoft.IdentityModel.Tokens;
using System.Security.Cryptography;
using VFR.ProfileApi.Features.QuickSetup;
using VFR.ProfileApi.Features.UpdateMeasurements;
using VFR.ProfileApi.Infrastructure;
using VFR.ProfileApi.Services;
using VFR.Protos;

var builder = WebApplication.CreateBuilder(args);

// ── Allow unencrypted HTTP/2 for gRPC (dev convenience) ──
AppContext.SetSwitch("System.Net.Http.SocketsHttpHandler.Http2UnencryptedSupport", true);

// ── Aspire service defaults (OpenTelemetry, health checks, service discovery) ──
builder.AddServiceDefaults();

// ── Database ──────────────────────────────────────────────────────────────────
builder.AddNpgsqlDbContext<ProfileDbContext>("profiles");

// ── Redis (distributed cache, future session storage) ─────────────────────────
builder.AddRedisClient("vfr-cache");

// ── JWT Bearer Authentication ─────────────────────────────────────────────────
// Must match ApplicationAuth.Common.Constants.AuthOptions exactly.
// Key = HMACSHA256(base64 KEY).Key — mirroring how ApplicationAuth.JWTService signs tokens.
var hmac = new HMACSHA256(Convert.FromBase64String(
    "1rsfje36ZtLDpEdNgc8H0lY8uDxSN5W42oB2qzaMZZkFyjnmtyDzbIqxRVvHsw7GIqNUUqYsyS2IkLVT6NH3JQ=="));

builder.Services
    .AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
    .AddJwtBearer(options =>
    {
        options.RequireHttpsMetadata = false; // allow plain HTTP in dev/Aspire
        options.SaveToken = true;
        options.TokenValidationParameters = new TokenValidationParameters
        {
            ValidateIssuer           = true,
            ValidIssuer              = "ApplicationAuthAuthServer",
            ValidateAudience         = true,
            ValidAudience            = "Client",
            ValidateIssuerSigningKey = true,
            IssuerSigningKey         = new SymmetricSecurityKey(hmac.Key),
            ValidateLifetime         = true,
        };
    });

builder.Services.AddAuthorization();

// ── Clean Slices ─────────────────────────────────────────────────────────────
// MediatR — scans this assembly for all IRequestHandler<,> implementations
builder.Services.AddMediatR(cfg =>
    cfg.RegisterServicesFromAssemblyContaining<QuickSetupHandler>());

// FluentValidation — scans this assembly for all AbstractValidator<> implementations
builder.Services.AddValidatorsFromAssemblyContaining<QuickSetupValidator>();

// ── Avatar gRPC Client (VFR.AiEngine) ───────────────────────────────────
// Aspire service discovery resolves "vfr-aiengine" at runtime.
// We configure the handler to bypass SSL validation for local dev/Docker scenarios.
builder.Services.AddGrpcClient<AvatarService.AvatarServiceClient>(o =>
{
    o.Address = new Uri("http://vfr-aiengine");
})
.ConfigurePrimaryHttpMessageHandler(() =>
{
    var handler = new HttpClientHandler();
    // Bypasses SSL certificate validation for local development
    handler.ServerCertificateCustomValidationCallback = 
        HttpClientHandler.DangerousAcceptAnyServerCertificateValidator;
    return handler;
})
.ConfigureChannel(o => o.UnsafeUseInsecureChannelCallCredentials = true);

builder.Services.AddScoped<IAvatarGenerationService, GrpcAvatarGenerationService>();

// ── RFC 7807 Problem Details ─────────────────────────────────────────────────
builder.Services.AddProblemDetails();

// ── API docs (dev only) ───────────────────────────────────────────────────────
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddOpenApi();

// ─────────────────────────────────────────────────────────────────────────────
var app = builder.Build();

// Apply EF migrations at startup (dev convenience — swap for a migration job in prod)
using (var scope = app.Services.CreateScope())
{
    var db = scope.ServiceProvider.GetRequiredService<ProfileDbContext>();
    await db.Database.MigrateAsync();
}

app.UseExceptionHandler();
app.UseStatusCodePages();
app.UseAuthentication();
app.UseAuthorization();

if (app.Environment.IsDevelopment())
{
    app.MapOpenApi();
}

// ── Profile API routes ────────────────────────────────────────────────────────
var profileGroup = app.MapGroup("/api/profile")
                      .WithTags("Profile");

profileGroup.MapQuickSetup();
profileGroup.MapUpdateMeasurements();

app.MapDefaultEndpoints(); // Aspire health checks

app.Run();
