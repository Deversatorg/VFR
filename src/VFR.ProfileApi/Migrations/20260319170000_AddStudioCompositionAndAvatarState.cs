using Microsoft.EntityFrameworkCore.Infrastructure;
using Microsoft.EntityFrameworkCore.Migrations;
using VFR.ProfileApi.Infrastructure;

#nullable disable

namespace VFR.ProfileApi.Migrations;

[DbContext(typeof(ProfileDbContext))]
[Migration("20260319170000_AddStudioCompositionAndAvatarState")]
public partial class AddStudioCompositionAndAvatarState : Migration
{
    protected override void Up(MigrationBuilder migrationBuilder)
    {
        migrationBuilder.AddColumn<decimal>(
            name: "BodyFatPercentage",
            table: "PhysicalProfiles",
            type: "numeric(5,2)",
            precision: 5,
            scale: 2,
            nullable: true);

        migrationBuilder.AddColumn<string>(
            name: "LastAvatarModelUrl",
            table: "PhysicalProfiles",
            type: "character varying(2048)",
            maxLength: 2048,
            nullable: true);

        migrationBuilder.AddColumn<decimal>(
            name: "Muscularity",
            table: "PhysicalProfiles",
            type: "numeric(5,2)",
            precision: 5,
            scale: 2,
            nullable: true);
    }

    protected override void Down(MigrationBuilder migrationBuilder)
    {
        migrationBuilder.DropColumn(name: "BodyFatPercentage", table: "PhysicalProfiles");
        migrationBuilder.DropColumn(name: "LastAvatarModelUrl", table: "PhysicalProfiles");
        migrationBuilder.DropColumn(name: "Muscularity", table: "PhysicalProfiles");
    }
}
