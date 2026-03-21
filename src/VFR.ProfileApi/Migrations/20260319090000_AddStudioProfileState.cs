using Microsoft.EntityFrameworkCore.Infrastructure;
using Microsoft.EntityFrameworkCore.Migrations;
using VFR.ProfileApi.Infrastructure;

#nullable disable

namespace VFR.ProfileApi.Migrations
{
    [DbContext(typeof(ProfileDbContext))]
    [Migration("20260319090000_AddStudioProfileState")]
    public partial class AddStudioProfileState : Migration
    {
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<decimal>(
                name: "ArmLength",
                table: "PhysicalProfiles",
                type: "numeric(6,2)",
                precision: 6,
                scale: 2,
                nullable: true);

            migrationBuilder.AddColumn<decimal>(
                name: "AutoArmLength",
                table: "PhysicalProfiles",
                type: "numeric(6,2)",
                precision: 6,
                scale: 2,
                nullable: true);

            migrationBuilder.AddColumn<decimal>(
                name: "AutoChestCircumference",
                table: "PhysicalProfiles",
                type: "numeric(6,2)",
                precision: 6,
                scale: 2,
                nullable: true);

            migrationBuilder.AddColumn<decimal>(
                name: "AutoHipCircumference",
                table: "PhysicalProfiles",
                type: "numeric(6,2)",
                precision: 6,
                scale: 2,
                nullable: true);

            migrationBuilder.AddColumn<decimal>(
                name: "AutoLegLength",
                table: "PhysicalProfiles",
                type: "numeric(6,2)",
                precision: 6,
                scale: 2,
                nullable: true);

            migrationBuilder.AddColumn<decimal>(
                name: "AutoWaistCircumference",
                table: "PhysicalProfiles",
                type: "numeric(6,2)",
                precision: 6,
                scale: 2,
                nullable: true);

            migrationBuilder.AddColumn<decimal>(
                name: "CalfCircumference",
                table: "PhysicalProfiles",
                type: "numeric(6,2)",
                precision: 6,
                scale: 2,
                nullable: true);

            migrationBuilder.AddColumn<string>(
                name: "Gender",
                table: "PhysicalProfiles",
                type: "text",
                nullable: false,
                defaultValue: "Neutral");

            migrationBuilder.AddColumn<decimal>(
                name: "LegLength",
                table: "PhysicalProfiles",
                type: "numeric(6,2)",
                precision: 6,
                scale: 2,
                nullable: true);

            migrationBuilder.AddColumn<decimal>(
                name: "TorsoLength",
                table: "PhysicalProfiles",
                type: "numeric(6,2)",
                precision: 6,
                scale: 2,
                nullable: true);
        }

        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropColumn(name: "ArmLength", table: "PhysicalProfiles");
            migrationBuilder.DropColumn(name: "AutoArmLength", table: "PhysicalProfiles");
            migrationBuilder.DropColumn(name: "AutoChestCircumference", table: "PhysicalProfiles");
            migrationBuilder.DropColumn(name: "AutoHipCircumference", table: "PhysicalProfiles");
            migrationBuilder.DropColumn(name: "AutoLegLength", table: "PhysicalProfiles");
            migrationBuilder.DropColumn(name: "AutoWaistCircumference", table: "PhysicalProfiles");
            migrationBuilder.DropColumn(name: "CalfCircumference", table: "PhysicalProfiles");
            migrationBuilder.DropColumn(name: "Gender", table: "PhysicalProfiles");
            migrationBuilder.DropColumn(name: "LegLength", table: "PhysicalProfiles");
            migrationBuilder.DropColumn(name: "TorsoLength", table: "PhysicalProfiles");
        }
    }
}
