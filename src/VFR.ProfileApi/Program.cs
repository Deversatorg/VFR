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

// ── JSON Serialization ────────────────────────────────────────────────────────
builder.Services.ConfigureHttpJsonOptions(options =>
{
    options.SerializerOptions.Converters.Add(new System.Text.Json.Serialization.JsonStringEnumConverter());
});

// ── JWT Bearer Authentication ─────────────────────────────────────────────────
// Key MUST match ApplicationAuth.Common.Constants.AuthOptions.GetSymmetricSecurityKey()
// which uses Encoding.ASCII.GetBytes(KEY) — NOT Convert.FromBase64String.
const string JWT_KEY = "1rsfje36ZtLDpEdNgc8H0lY8uDxSN5W42oB2qzaMZZkFyjnmtyDzbIqxRVvHsw7GIqNUUqYsyS2IkLVT6NH3JQ==";
var signingKeyBytes = System.Text.Encoding.ASCII.GetBytes(JWT_KEY);
Console.WriteLine($"[JWT DEBUG] ProfileApi signing key length: {signingKeyBytes.Length} bytes, first 4: {signingKeyBytes[0]:X2}{signingKeyBytes[1]:X2}{signingKeyBytes[2]:X2}{signingKeyBytes[3]:X2}");

builder.Services
    .AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
    .AddJwtBearer(options =>
    {
        options.RequireHttpsMetadata = false;
        options.SaveToken = true;
        options.TokenValidationParameters = new TokenValidationParameters
        {
            ValidateIssuer           = true,
            ValidIssuer              = "ApplicationAuthAuthServer",
            ValidateAudience         = true,
            ValidAudience            = "Client",
            ValidateIssuerSigningKey = true,
            IssuerSigningKey         = new SymmetricSecurityKey(signingKeyBytes),
            ValidateLifetime         = true,
        };
        options.Events = new Microsoft.AspNetCore.Authentication.JwtBearer.JwtBearerEvents
        {
            OnAuthenticationFailed = ctx =>
            {
                Console.WriteLine($"[JWT AUTH FAILED] {ctx.Exception.GetType().Name}: {ctx.Exception.Message}");
                return Task.CompletedTask;
            },
            OnTokenValidated = ctx =>
            {
                Console.WriteLine($"[JWT AUTH OK] User: {ctx.Principal?.Identity?.Name}");
                return Task.CompletedTask;
            },
            OnChallenge = ctx =>
            {
                Console.WriteLine($"[JWT CHALLENGE] Error: {ctx.Error}, Desc: {ctx.ErrorDescription}");
                return Task.CompletedTask;
            }
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
    o.Address = new Uri("http://_grpc.vfr-aiengine");
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

// ── CORS ──────────────────────────────────────────────────────────────────────
builder.Services.AddCors(options =>
{
    options.AddDefaultPolicy(policy =>
    {
        if (builder.Environment.IsDevelopment())
        {
            // Allow any localhost port (needed for Aspire dynamic port assignment)
            policy.SetIsOriginAllowed(origin =>
                    new Uri(origin).Host == "localhost" || new Uri(origin).Host == "127.0.0.1")
                  .AllowAnyHeader()
                  .AllowAnyMethod()
                  .AllowCredentials();
        }
        else
        {
            policy.WithOrigins("https://yourdomain.com")
                  .AllowAnyHeader()
                  .AllowAnyMethod();
        }
    });
});

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
app.UseCors();
app.UseAuthentication();
app.UseAuthorization();

if (app.Environment.IsDevelopment())
{
    app.MapOpenApi();
}

// ── Profile API routes ────────────────────────────────────────────────────────
var profileGroup = app.MapGroup("/api/v1/profiles")
                      .WithTags("Profile");

profileGroup.MapQuickSetup();
profileGroup.MapUpdateMeasurements();

app.MapDefaultEndpoints(); // Aspire health checks

app.Run();
