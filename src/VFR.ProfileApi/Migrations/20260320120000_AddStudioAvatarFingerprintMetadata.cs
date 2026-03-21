using Microsoft.EntityFrameworkCore.Infrastructure;
using Microsoft.EntityFrameworkCore.Migrations;
using VFR.ProfileApi.Infrastructure;

#nullable disable

namespace VFR.ProfileApi.Migrations;

[DbContext(typeof(ProfileDbContext))]
[Migration("20260320120000_AddStudioAvatarFingerprintMetadata")]
public partial class AddStudioAvatarFingerprintMetadata : Migration
{
    protected override void Up(MigrationBuilder migrationBuilder)
    {
        migrationBuilder.AddColumn<DateTime>(
            name: "LastAvatarGeneratedAt",
            table: "PhysicalProfiles",
            type: "timestamp with time zone",
            nullable: true);

        migrationBuilder.AddColumn<string>(
            name: "LastAvatarInputHash",
            table: "PhysicalProfiles",
            type: "character varying(128)",
            maxLength: 128,
            nullable: true);
    }

    protected override void Down(MigrationBuilder migrationBuilder)
    {
        migrationBuilder.DropColumn(name: "LastAvatarGeneratedAt", table: "PhysicalProfiles");
        migrationBuilder.DropColumn(name: "LastAvatarInputHash", table: "PhysicalProfiles");
    }
}
