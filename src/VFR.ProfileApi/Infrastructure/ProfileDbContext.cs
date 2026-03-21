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
            e.Property(p => p.Gender).HasConversion<string>();
            e.Property(p => p.Muscularity).HasPrecision(5, 2);
            e.Property(p => p.BodyFatPercentage).HasPrecision(5, 2);
            e.Property(p => p.LastAvatarModelUrl).HasMaxLength(2048);
            e.Property(p => p.LastAvatarGeneratedAt);
            e.Property(p => p.LastAvatarInputHash).HasMaxLength(128);

            e.Property(p => p.ChestCircumference).HasPrecision(6, 2);
            e.Property(p => p.WaistCircumference).HasPrecision(6, 2);
            e.Property(p => p.HipCircumference).HasPrecision(6, 2);
            e.Property(p => p.ShoulderWidth).HasPrecision(6, 2);
            e.Property(p => p.CalfCircumference).HasPrecision(6, 2);
            e.Property(p => p.ArmLength).HasPrecision(6, 2);
            e.Property(p => p.TorsoLength).HasPrecision(6, 2);
            e.Property(p => p.LegLength).HasPrecision(6, 2);

            e.Property(p => p.AutoChestCircumference).HasPrecision(6, 2);
            e.Property(p => p.AutoWaistCircumference).HasPrecision(6, 2);
            e.Property(p => p.AutoHipCircumference).HasPrecision(6, 2);
            e.Property(p => p.AutoArmLength).HasPrecision(6, 2);
            e.Property(p => p.AutoLegLength).HasPrecision(6, 2);

            e.Property(p => p.CreatedAt).HasDefaultValueSql("now()");
            e.Property(p => p.UpdatedAt).HasDefaultValueSql("now()");
        });
    }
}
