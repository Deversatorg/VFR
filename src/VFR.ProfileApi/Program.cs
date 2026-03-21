using FluentValidation;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.EntityFrameworkCore;
using Microsoft.IdentityModel.Tokens;
using VFR.ProfileApi.Features.GetProfile;
using VFR.ProfileApi.Features.QuickSetup;
using VFR.ProfileApi.Features.UpdateMeasurements;
using VFR.ProfileApi.Features.UpsertStudioProfile;
using VFR.ProfileApi.Infrastructure;

var builder = WebApplication.CreateBuilder(args);

// Aspire service defaults: OpenTelemetry, health checks, service discovery.
builder.AddServiceDefaults();

// Database
builder.AddNpgsqlDbContext<ProfileDbContext>("profiles");

// Redis
builder.AddRedisClient("vfr-cache");

// JSON serialization
builder.Services.ConfigureHttpJsonOptions(options =>
{
    options.SerializerOptions.Converters.Add(new System.Text.Json.Serialization.JsonStringEnumConverter());
});

var jwtIssuer = builder.Configuration["Jwt:Issuer"]?.Trim() ?? "ApplicationAuthAuthServer";
var jwtAudience = builder.Configuration["Jwt:Audience"]?.Trim() ?? "Client";
var jwtSigningKey = builder.Configuration["Jwt:SigningKey"]?.Trim();
if (string.IsNullOrWhiteSpace(jwtSigningKey))
{
    if (builder.Environment.IsEnvironment("Testing"))
    {
        jwtSigningKey = "integration-tests-signing-key-1234567890";
    }
    else
    {
        throw new InvalidOperationException("JWT signing key is not configured. Set Jwt:SigningKey.");
    }
}

var allowedCorsOrigins = builder.Configuration
    .GetSection("Cors:AllowedOrigins")
    .Get<string[]>()?
    .Where(origin => !string.IsNullOrWhiteSpace(origin))
    .Distinct(StringComparer.OrdinalIgnoreCase)
    .ToArray() ?? Array.Empty<string>();

static bool IsLocalDevelopmentOrigin(string? origin)
{
    if (string.IsNullOrWhiteSpace(origin) || !Uri.TryCreate(origin, UriKind.Absolute, out var uri))
    {
        return false;
    }

    return (uri.Scheme == Uri.UriSchemeHttp || uri.Scheme == Uri.UriSchemeHttps)
        && (uri.Host.Equals("localhost", StringComparison.OrdinalIgnoreCase)
            || uri.Host.Equals("127.0.0.1", StringComparison.OrdinalIgnoreCase));
}

builder.Services
    .AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
    .AddJwtBearer(options =>
    {
        options.SaveToken = true;
        options.TokenValidationParameters = new TokenValidationParameters
        {
            ValidateIssuer = true,
            ValidIssuer = jwtIssuer,
            ValidateAudience = true,
            ValidAudience = jwtAudience,
            ValidateIssuerSigningKey = true,
            IssuerSigningKey = new SymmetricSecurityKey(System.Text.Encoding.ASCII.GetBytes(jwtSigningKey)),
            ValidateLifetime = true,
        };
    });

builder.Services.AddAuthorization();

// Clean slices
builder.Services.AddMediatR(cfg =>
    cfg.RegisterServicesFromAssemblyContaining<QuickSetupHandler>());
builder.Services.AddValidatorsFromAssemblyContaining<QuickSetupValidator>();

// RFC 7807 problem details
builder.Services.AddProblemDetails();

// CORS
builder.Services.AddCors(options =>
{
    options.AddDefaultPolicy(policy =>
    {
        if (allowedCorsOrigins.Length > 0)
        {
            policy.WithOrigins(allowedCorsOrigins)
                .AllowAnyHeader()
                .AllowAnyMethod();
        }
        else
        {
            policy.SetIsOriginAllowed(IsLocalDevelopmentOrigin)
                .AllowAnyHeader()
                .AllowAnyMethod();
        }
    });
});

// API docs
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddOpenApi();

var app = builder.Build();

// Allow tests to replace the provider without trying to run PostgreSQL migrations.
if (!DatabaseBootstrapControl.ShouldSkip(builder.Configuration))
{
    using var scope = app.Services.CreateScope();
    var db = scope.ServiceProvider.GetRequiredService<ProfileDbContext>();
    await db.Database.MigrateAsync();
}

app.UseExceptionHandler();
app.UseStatusCodePages();
app.UseRouting();
app.UseCors();
app.UseAuthentication();
app.UseAuthorization();

if (app.Environment.IsDevelopment())
{
    app.MapOpenApi();
}

var profileGroup = app.MapGroup("/api/v1/profiles")
    .WithTags("Profile");

profileGroup.MapGetProfile();
profileGroup.MapQuickSetup();
profileGroup.MapUpdateMeasurements();
profileGroup.MapUpsertStudioProfile();

app.MapDefaultEndpoints();

app.Run();
