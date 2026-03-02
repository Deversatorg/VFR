using Microsoft.EntityFrameworkCore;
using VFR.ProfileApi.Domain;

namespace VFR.ProfileApi.Infrastructure;

public sealed class ProfileDbContext(DbContextOptions<ProfileDbContext> options)
    : DbContext(options)
{
    public DbSet<PhysicalProfile> PhysicalProfiles => Set<PhysicalProfile>();

    protected override void OnModelCreating(ModelBuilder builder)
    {
        base.OnModelCreating(builder);

        builder.Entity<PhysicalProfile>(e =>
        {
            e.HasKey(p => p.Id);

            e.HasIndex(p => p.UserId).IsUnique(); // one profile per user

            e.Property(p => p.UserId).HasMaxLength(450).IsRequired();
            e.Property(p => p.Height).HasPrecision(6, 2);
            e.Property(p => p.Weight).HasPrecision(6, 2);
            e.Property(p => p.BodyType).HasConversion<string>();

            e.Property(p => p.ChestCircumference).HasPrecision(6, 2);
            e.Property(p => p.WaistCircumference).HasPrecision(6, 2);
            e.Property(p => p.HipCircumference).HasPrecision(6, 2);
            e.Property(p => p.ShoulderWidth).HasPrecision(6, 2);

            e.Property(p => p.CreatedAt).HasDefaultValueSql("now()");
            e.Property(p => p.UpdatedAt).HasDefaultValueSql("now()");
        });
    }
}
