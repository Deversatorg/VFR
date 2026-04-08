using System;
using ApplicationAuth.DAL;
using Microsoft.EntityFrameworkCore.Infrastructure;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace ApplicationAuth.DAL.Migrations
{
    [DbContext(typeof(DataContext))]
    [Migration("20260322170000_AddStripeEventTrackingToSubscriptions")]
    public partial class AddStripeEventTrackingToSubscriptions : Migration
    {
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<DateTime>(
                name: "LastStripeEventCreatedAt",
                table: "Subscriptions",
                type: "timestamp with time zone",
                nullable: true);

            migrationBuilder.AddColumn<string>(
                name: "LastStripeEventId",
                table: "Subscriptions",
                type: "character varying(200)",
                maxLength: 200,
                nullable: true);
        }

        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropColumn(
                name: "LastStripeEventCreatedAt",
                table: "Subscriptions");

            migrationBuilder.DropColumn(
                name: "LastStripeEventId",
                table: "Subscriptions");
        }
    }
}
