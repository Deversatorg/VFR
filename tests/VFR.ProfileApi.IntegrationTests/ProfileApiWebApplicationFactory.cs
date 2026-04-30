using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.DataProtection;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Infrastructure;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using VFR.ProfileApi.Features.StudioAvatarGeneration;
using VFR.ProfileApi.Features.QuickSetup;
using VFR.ProfileApi.Infrastructure;

namespace VFR.ProfileApi.IntegrationTests;

public sealed class ProfileApiWebApplicationFactory : WebApplicationFactory<QuickSetupHandler>
{
    private readonly string _databaseName = $"profile-api-tests-{Guid.NewGuid():N}";
    private readonly string? _aiEngineBaseUrl;
    private readonly IAiEngineClient? _aiEngineClient;

    public ProfileApiWebApplicationFactory()
    {
    }

    internal ProfileApiWebApplicationFactory(string aiEngineBaseUrl)
    {
        _aiEngineBaseUrl = aiEngineBaseUrl;
    }

    internal ProfileApiWebApplicationFactory(IAiEngineClient aiEngineClient)
    {
        _aiEngineClient = aiEngineClient;
    }

    protected override void ConfigureWebHost(IWebHostBuilder builder)
    {
        builder.UseEnvironment("Testing");
        builder.ConfigureLogging(logging => logging.ClearProviders());
        builder.ConfigureAppConfiguration((_, config) =>
        {
            var values = new Dictionary<string, string?>(TestHostDefaults.Configuration);
            if (!string.IsNullOrWhiteSpace(_aiEngineBaseUrl))
            {
                values["AiEngine:BaseUrl"] = _aiEngineBaseUrl;
            }

            config.AddInMemoryCollection(values);
        });

        builder.ConfigureServices(services =>
        {
            services.RemoveAll(typeof(DbContextOptions<ProfileDbContext>));
            services.RemoveAll(typeof(IDbContextOptionsConfiguration<ProfileDbContext>));
            services.RemoveAll(typeof(ProfileDbContext));

            services.AddDbContext<ProfileDbContext>(options =>
            {
                options.UseInMemoryDatabase(_databaseName);
            });

            services.AddDataProtection()
                .UseEphemeralDataProtectionProvider();

            services.AddAuthentication(options =>
                {
                    options.DefaultAuthenticateScheme = TestAuthHandler.SchemeName;
                    options.DefaultChallengeScheme = TestAuthHandler.SchemeName;
                    options.DefaultScheme = TestAuthHandler.SchemeName;
                })
                .AddScheme<AuthenticationSchemeOptions, TestAuthHandler>(TestAuthHandler.SchemeName, _ => { });

            if (_aiEngineClient is not null)
            {
                services.RemoveAll<IAiEngineClient>();
                services.AddSingleton(_aiEngineClient);
            }
        });
    }

    protected override IHost CreateHost(IHostBuilder builder)
    {
        var host = base.CreateHost(builder);

        using var scope = host.Services.CreateScope();
        var db = scope.ServiceProvider.GetRequiredService<ProfileDbContext>();
        db.Database.EnsureCreated();

        return host;
    }

    public HttpClient CreateAuthenticatedClient(string userId = "integration-user")
    {
        var client = CreateClient();
        client.DefaultRequestHeaders.Add(TestAuthHandler.UserIdHeaderName, userId);
        return client;
    }
}
