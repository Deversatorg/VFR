using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using System.Text.Json.Serialization;
using VFR.ProfileApi.Domain;
using VFR.ProfileApi.Features.GetProfile;
using VFR.ProfileApi.Features.QuickSetup;
using VFR.ProfileApi.Features.UpsertStudioProfile;
using Xunit;

namespace VFR.ProfileApi.IntegrationTests;

public sealed class ProfileEndpointsTests : IClassFixture<ProfileApiWebApplicationFactory>
{
    private static readonly JsonSerializerOptions JsonOptions = new(JsonSerializerDefaults.Web)
    {
        Converters = { new JsonStringEnumConverter() }
    };

    private readonly ProfileApiWebApplicationFactory _factory;

    public ProfileEndpointsTests(ProfileApiWebApplicationFactory factory)
    {
        _factory = factory;
    }

    [Fact]
    public async Task GetProfile_ReturnsNotFound_WhenProfileDoesNotExist()
    {
        using var client = _factory.CreateAuthenticatedClient("missing-user");

        var response = await client.GetAsync("/api/v1/profiles/me");

        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
    }

    [Fact]
    public async Task QuickSetup_CreatesProfileThatCanBeFetched()
    {
        using var client = _factory.CreateAuthenticatedClient("quick-setup-user");

        var setupResponse = await client.PostAsJsonAsync(
            "/api/v1/profiles/quick-setup",
            new QuickSetupRequest(Height: 182m, Weight: 79m, BodyType: BodyType.Athletic),
            JsonOptions);

        Assert.Equal(HttpStatusCode.OK, setupResponse.StatusCode);

        var setupPayload = await setupResponse.Content.ReadFromJsonAsync<QuickSetupResult>();
        Assert.NotNull(setupPayload);
        Assert.NotEqual(Guid.Empty, setupPayload!.ProfileId);

        var profile = await client.GetFromJsonAsync<GetProfileResponse>("/api/v1/profiles/me");

        Assert.NotNull(profile);
        Assert.Equal("quick-setup-user", profile!.UserId);
        Assert.Equal(182d, profile.Height);
        Assert.Equal(79d, profile.Weight);
        Assert.Equal(nameof(BodyType.Athletic), profile.BodyType);
    }

    [Fact]
    public async Task UpsertStudioProfile_StoresManualAndAutoMeasurements()
    {
        using var client = _factory.CreateAuthenticatedClient("studio-user");

        var response = await client.PutAsJsonAsync(
            "/api/v1/profiles/me/studio",
            new UpsertStudioProfileRequest(
                Height: 175m,
                Weight: 68m,
                BodyType: BodyType.Regular,
                Gender: AvatarGender.Female,
                Muscularity: 28m,
                BodyFatPercentage: 19m,
                ChestCircumference: 92m,
                WaistCircumference: 70m,
                HipCircumference: 96m,
                ShoulderWidth: 41m,
                CalfCircumference: 35m,
                ArmLength: 58m,
                TorsoLength: 61m,
                LegLength: 103m,
                AutoChestCircumference: 91m,
                AutoWaistCircumference: 69m,
                AutoHipCircumference: 95m,
                AutoArmLength: 57m,
                AutoLegLength: 102m,
                GeneratedAvatar: new UpsertStudioGeneratedAvatarRequest(
                    ModelUrl: "https://cdn.example.com/models/studio-user.glb",
                    GeneratedAt: new DateTime(2026, 3, 20, 11, 30, 0, DateTimeKind.Utc))),
            JsonOptions);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);

        var profile = await response.Content.ReadFromJsonAsync<GetProfileResponse>();
        Assert.NotNull(profile);
        Assert.Equal("studio-user", profile!.UserId);
        Assert.Equal(nameof(AvatarGender.Female), profile.Gender);
        Assert.Equal(28d, profile.Muscularity);
        Assert.Equal(19d, profile.BodyFatPercentage);
        Assert.Equal("https://cdn.example.com/models/studio-user.glb", profile.GeneratedAvatar.ModelUrl);
        Assert.True(profile.GeneratedAvatar.IsCurrent);
        Assert.False(string.IsNullOrWhiteSpace(profile.DraftStateHash));
        Assert.Equal(92d, profile.ManualMeasurements.ChestCircumference);
        Assert.Equal(69d, profile.AutoMeasurements.WaistCircumference);

        var fetched = await client.GetFromJsonAsync<GetProfileResponse>("/api/v1/profiles/me");
        Assert.NotNull(fetched);
        Assert.Equal(96d, fetched!.ManualMeasurements.HipCircumference);
        Assert.Equal(102d, fetched.AutoMeasurements.LegLength);
        Assert.Equal("https://cdn.example.com/models/studio-user.glb", fetched.GeneratedAvatar.ModelUrl);
        Assert.True(fetched.GeneratedAvatar.IsCurrent);
    }

    [Fact]
    public async Task UpsertStudioProfile_PreservesGeneratedAvatar_WhenSavingDraftOnly()
    {
        using var client = _factory.CreateAuthenticatedClient("studio-draft-user");

        var initialResponse = await client.PutAsJsonAsync(
            "/api/v1/profiles/me/studio",
            new UpsertStudioProfileRequest(
                Height: 178m,
                Weight: 74m,
                BodyType: BodyType.Athletic,
                Gender: AvatarGender.Male,
                Muscularity: 64m,
                BodyFatPercentage: 15m,
                ChestCircumference: 101m,
                WaistCircumference: 84m,
                HipCircumference: 97m,
                ShoulderWidth: 45m,
                CalfCircumference: 37m,
                ArmLength: 62m,
                TorsoLength: 63m,
                LegLength: 107m,
                AutoChestCircumference: 100m,
                AutoWaistCircumference: 83m,
                AutoHipCircumference: 96m,
                AutoArmLength: 61m,
                AutoLegLength: 106m,
                GeneratedAvatar: new UpsertStudioGeneratedAvatarRequest(
                    ModelUrl: "https://cdn.example.com/models/studio-draft-user-v1.glb",
                    GeneratedAt: new DateTime(2026, 3, 20, 12, 0, 0, DateTimeKind.Utc))),
            JsonOptions);

        Assert.Equal(HttpStatusCode.OK, initialResponse.StatusCode);

        var draftOnlyResponse = await client.PutAsJsonAsync(
            "/api/v1/profiles/me/studio",
            new UpsertStudioProfileRequest(
                Height: 178m,
                Weight: 76m,
                BodyType: BodyType.Athletic,
                Gender: AvatarGender.Male,
                Muscularity: 64m,
                BodyFatPercentage: 15m,
                ChestCircumference: 101m,
                WaistCircumference: 84m,
                HipCircumference: 97m,
                ShoulderWidth: 45m,
                CalfCircumference: 37m,
                ArmLength: 62m,
                TorsoLength: 63m,
                LegLength: 107m,
                AutoChestCircumference: 100m,
                AutoWaistCircumference: 83m,
                AutoHipCircumference: 96m,
                AutoArmLength: 61m,
                AutoLegLength: 106m,
                GeneratedAvatar: null),
            JsonOptions);

        Assert.Equal(HttpStatusCode.OK, draftOnlyResponse.StatusCode);

        var profile = await draftOnlyResponse.Content.ReadFromJsonAsync<GetProfileResponse>();
        Assert.NotNull(profile);
        Assert.Equal("https://cdn.example.com/models/studio-draft-user-v1.glb", profile!.GeneratedAvatar.ModelUrl);
        Assert.False(profile.GeneratedAvatar.IsCurrent);
        Assert.NotEqual(profile.DraftStateHash, profile.GeneratedAvatar.InputHash);

        var fetched = await client.GetFromJsonAsync<GetProfileResponse>("/api/v1/profiles/me");
        Assert.NotNull(fetched);
        Assert.Equal("https://cdn.example.com/models/studio-draft-user-v1.glb", fetched!.GeneratedAvatar.ModelUrl);
        Assert.False(fetched.GeneratedAvatar.IsCurrent);
    }
}
