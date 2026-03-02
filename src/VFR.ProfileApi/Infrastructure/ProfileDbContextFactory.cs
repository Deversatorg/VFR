using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Design;

namespace VFR.ProfileApi.Infrastructure;

/// <summary>
/// Design-time factory so EF Core tooling (migrations) can instantiate ProfileDbContext
/// without running the full application host.  Not used at runtime.
/// </summary>
public sealed class ProfileDbContextFactory : IDesignTimeDbContextFactory<ProfileDbContext>
{
    public ProfileDbContext CreateDbContext(string[] args)
    {
        var optionsBuilder = new DbContextOptionsBuilder<ProfileDbContext>();

        // Use a placeholder connection string for migration scaffolding.
        // The real connection string is injected by Aspire at runtime.
        optionsBuilder.UseNpgsql(
            "Host=localhost;Database=profiles;Username=postgres;Password=postgres");

        return new ProfileDbContext(optionsBuilder.Options);
    }
}
