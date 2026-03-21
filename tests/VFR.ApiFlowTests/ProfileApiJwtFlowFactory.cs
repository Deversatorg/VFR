using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.AspNetCore.DataProtection;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Infrastructure;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using VFR.ProfileApi.Features.QuickSetup;
using VFR.ProfileApi.Infrastructure;

namespace VFR.ApiFlowTests;

public sealed class ProfileApiJwtFlowFactory : WebApplicationFactory<QuickSetupHandler>
{
    private readonly string _databaseName = $"profile-api-jwt-flow-tests-{Guid.NewGuid():N}";

    protected override void ConfigureWebHost(IWebHostBuilder builder)
    {
        builder.UseEnvironment("Testing");
        builder.ConfigureLogging(logging => logging.ClearProviders());
        builder.ConfigureAppConfiguration((_, config) =>
        {
            config.AddInMemoryCollection(TestHostDefaults.Configuration);
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
}
