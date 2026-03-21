using ApplicationAuth.Common.Constants;
using ApplicationAuth.DAL;
using ApplicationAuth.DAL.Abstract;
using ApplicationAuth.Domain.Entities.Identity;
using ApplicationAuth.Features.Account.Login;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;
using Microsoft.Extensions.Hosting;

namespace ApplicationAuth.IntegrationTests;

public sealed class ApplicationAuthWebApplicationFactory : WebApplicationFactory<LoginHandler>
{
    private readonly string _databaseName = $"application-auth-tests-{Guid.NewGuid():N}";

    protected override void ConfigureWebHost(IWebHostBuilder builder)
    {
        builder.UseEnvironment("Testing");
        builder.ConfigureAppConfiguration((_, config) =>
        {
            config.AddInMemoryCollection(TestHostDefaults.Configuration);
        });

        builder.ConfigureServices(services =>
        {
            services.RemoveAll(typeof(DbContextOptions<DataContext>));
            services.RemoveAll(typeof(DataContext));
            services.RemoveAll(typeof(IDataContext));

            services.AddDbContext<DataContext>(options =>
            {
                options.UseInMemoryDatabase(_databaseName);
            });

            services.AddScoped<IDataContext>(sp => sp.GetRequiredService<DataContext>());
        });
    }

    protected override IHost CreateHost(IHostBuilder builder)
    {
        var host = base.CreateHost(builder);

        using var scope = host.Services.CreateScope();
        var services = scope.ServiceProvider;
        var db = services.GetRequiredService<DataContext>();
        db.Database.EnsureCreated();

        var roleManager = services.GetRequiredService<RoleManager<ApplicationRole>>();
        SeedRolesAsync(roleManager).GetAwaiter().GetResult();

        return host;
    }

    public async Task ConfirmAndActivateUserAsync(string email)
    {
        using var scope = Services.CreateScope();
        var userManager = scope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>();
        var user = await userManager.FindByEmailAsync(email);

        if (user is null)
        {
            throw new InvalidOperationException($"User '{email}' was not found.");
        }

        user.EmailConfirmed = true;
        user.IsActive = true;

        var result = await userManager.UpdateAsync(user);
        if (!result.Succeeded)
        {
            throw new InvalidOperationException(
                $"Failed to confirm test user '{email}': {string.Join(", ", result.Errors.Select(x => x.Description))}");
        }
    }

    private static async Task SeedRolesAsync(RoleManager<ApplicationRole> roleManager)
    {
        foreach (var role in new[] { Role.User, Role.Admin, Role.SuperAdmin })
        {
            if (!await roleManager.RoleExistsAsync(role))
            {
                var result = await roleManager.CreateAsync(new ApplicationRole { Name = role });
                if (!result.Succeeded)
                {
                    throw new InvalidOperationException(
                        $"Failed to seed role '{role}': {string.Join(", ", result.Errors.Select(x => x.Description))}");
                }
            }
        }
    }
}
