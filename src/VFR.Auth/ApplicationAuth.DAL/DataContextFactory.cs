using System;
using System.Linq;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Design;

namespace ApplicationAuth.DAL;

public sealed class DataContextFactory : IDesignTimeDbContextFactory<DataContext>
{
    public DataContext CreateDbContext(string[] args)
    {
        var connectionString =
            Environment.GetEnvironmentVariable("ConnectionStrings__Connection")
            ?? Environment.GetEnvironmentVariable("ConnectionStrings:Connection")
            ?? args.FirstOrDefault(arg => arg.StartsWith("Host=", StringComparison.OrdinalIgnoreCase))
            ?? "Host=localhost;Port=5432;Username=postgres;Password=postgres;Database=auth";

        var optionsBuilder = new DbContextOptionsBuilder<DataContext>();
        optionsBuilder.UseNpgsql(connectionString);
        return new DataContext(optionsBuilder.Options);
    }
}
