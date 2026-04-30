using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using System.Text.Json.Serialization;
using VFR.ProfileApi.Domain;
using VFR.ProfileApi.Features.GetProfile;
using VFR.ProfileApi.Features.StudioAvatarGeneration;
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
        Assert.Null(profile.GeneratedAvatar.ModelUrl);
        Assert.Null(profile.GeneratedAvatar.GeneratedAt);
        Assert.Null(profile.GeneratedAvatar.InputHash);
        Assert.False(profile.GeneratedAvatar.IsCurrent);
        Assert.False(string.IsNullOrWhiteSpace(profile.DraftStateHash));
        Assert.Equal(92d, profile.ManualMeasurements.ChestCircumference);
        Assert.Equal(69d, profile.AutoMeasurements.WaistCircumference);

        var fetched = await client.GetFromJsonAsync<GetProfileResponse>("/api/v1/profiles/me");
        Assert.NotNull(fetched);
        Assert.Equal(96d, fetched!.ManualMeasurements.HipCircumference);
        Assert.Equal(102d, fetched.AutoMeasurements.LegLength);
        Assert.Null(fetched.GeneratedAvatar.ModelUrl);
        Assert.False(fetched.GeneratedAvatar.IsCurrent);
    }

    [Fact]
    public async Task UpsertStudioProfile_PreservesGeneratedAvatar_WhenSavingDraftOnly()
    {
        var aiClient = new FakeAiEngineClient();
        using var factory = new ProfileApiWebApplicationFactory(aiClient);
        using var client = factory.CreateAuthenticatedClient("studio-draft-user");

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
                AutoArmLength: null,
                AutoLegLength: null,
                GeneratedAvatar: null),
            JsonOptions);

        Assert.Equal(HttpStatusCode.OK, initialResponse.StatusCode);

        var enqueueResponse = await client.PostAsync(
            "/api/v1/profiles/me/studio/avatar-generation",
            content: null);

        Assert.Equal(HttpStatusCode.OK, enqueueResponse.StatusCode);

        var enqueuePayload = await enqueueResponse.Content.ReadFromJsonAsync<StudioAvatarGenerationStartResponse>();
        Assert.NotNull(enqueuePayload);

        var generatedStatus = await client.GetFromJsonAsync<StudioAvatarGenerationStatusResponse>(
            $"/api/v1/profiles/me/studio/avatar-generation/{enqueuePayload!.TaskId}");

        Assert.NotNull(generatedStatus);
        Assert.Equal("SUCCESS", generatedStatus!.Status);
        Assert.Equal("http://ai.test/models/generated-avatar.glb", generatedStatus.Result!.Profile.GeneratedAvatar.ModelUrl);

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
                GeneratedAvatar: new UpsertStudioGeneratedAvatarRequest(
                    ModelUrl: "https://cdn.example.com/models/malicious-replacement.glb",
                    GeneratedAt: new DateTime(2026, 3, 20, 12, 0, 0, DateTimeKind.Utc))),
            JsonOptions);

        Assert.Equal(HttpStatusCode.OK, draftOnlyResponse.StatusCode);

        var profile = await draftOnlyResponse.Content.ReadFromJsonAsync<GetProfileResponse>();
        Assert.NotNull(profile);
        Assert.Equal("http://ai.test/models/generated-avatar.glb", profile!.GeneratedAvatar.ModelUrl);
        Assert.False(profile.GeneratedAvatar.IsCurrent);
        Assert.NotEqual(profile.DraftStateHash, profile.GeneratedAvatar.InputHash);

        var fetched = await client.GetFromJsonAsync<GetProfileResponse>("/api/v1/profiles/me");
        Assert.NotNull(fetched);
        Assert.Equal("http://ai.test/models/generated-avatar.glb", fetched!.GeneratedAvatar.ModelUrl);
        Assert.False(fetched.GeneratedAvatar.IsCurrent);
    }

    [Fact]
    public async Task StudioAvatarGeneration_BrokersAiAndPersistsGeneratedAvatar()
    {
        var aiClient = new FakeAiEngineClient();
        using var factory = new ProfileApiWebApplicationFactory(aiClient);
        using var client = factory.CreateAuthenticatedClient("studio-generation-user");

        var upsertResponse = await client.PutAsJsonAsync(
            "/api/v1/profiles/me/studio",
            new UpsertStudioProfileRequest(
                Height: 181m,
                Weight: 77m,
                BodyType: BodyType.Athletic,
                Gender: AvatarGender.Male,
                Muscularity: 72m,
                BodyFatPercentage: 14m,
                ChestCircumference: 101m,
                WaistCircumference: 83m,
                HipCircumference: 98m,
                ShoulderWidth: 46m,
                CalfCircumference: 38m,
                ArmLength: 62m,
                TorsoLength: 64m,
                LegLength: 108m,
                AutoChestCircumference: null,
                AutoWaistCircumference: null,
                AutoHipCircumference: null,
                AutoArmLength: null,
                AutoLegLength: null,
                GeneratedAvatar: null),
            JsonOptions);

        Assert.Equal(HttpStatusCode.OK, upsertResponse.StatusCode);

        var enqueueResponse = await client.PostAsync(
            "/api/v1/profiles/me/studio/avatar-generation",
            content: null);

        Assert.Equal(HttpStatusCode.OK, enqueueResponse.StatusCode);

        var enqueuePayload = await enqueueResponse.Content.ReadFromJsonAsync<StudioAvatarGenerationStartResponse>();
        Assert.NotNull(enqueuePayload);
        Assert.Equal("accepted", enqueuePayload!.Status);
        Assert.False(string.IsNullOrWhiteSpace(enqueuePayload.TaskId));

        Assert.NotNull(aiClient.LastProfile);
        Assert.Equal("studio-generation-user", aiClient.LastProfile!.UserId);
        Assert.Equal(BodyType.Athletic, aiClient.LastProfile.BodyType);
        Assert.Equal(AvatarGender.Male, aiClient.LastProfile.Gender);

        var status = await client.GetFromJsonAsync<StudioAvatarGenerationStatusResponse>(
            $"/api/v1/profiles/me/studio/avatar-generation/{enqueuePayload.TaskId}");

        Assert.NotNull(status);
        Assert.Equal("SUCCESS", status!.Status);
        Assert.NotNull(status.Result);
        Assert.Equal("http://ai.test/models/generated-avatar.glb", status.Result!.ModelUrl);
        Assert.Equal(102d, status.Result.Measurements["chest_cm"]);
        Assert.Equal("http://ai.test/models/generated-avatar.glb", status.Result.Profile.GeneratedAvatar.ModelUrl);
        Assert.True(status.Result.Profile.GeneratedAvatar.IsCurrent);
        Assert.Equal(84d, status.Result.Profile.AutoMeasurements.WaistCircumference);

        var fetched = await client.GetFromJsonAsync<GetProfileResponse>("/api/v1/profiles/me");
        Assert.NotNull(fetched);
        Assert.Equal("http://ai.test/models/generated-avatar.glb", fetched!.GeneratedAvatar.ModelUrl);
        Assert.True(fetched.GeneratedAvatar.IsCurrent);
    }

    [Fact]
    public async Task StudioAvatarGeneration_ReturnsStale_WhenDraftChangedBeforeSuccess()
    {
        var aiClient = new FakeAiEngineClient();
        using var factory = new ProfileApiWebApplicationFactory(aiClient);
        using var client = factory.CreateAuthenticatedClient("studio-stale-user");

        var initialResponse = await client.PutAsJsonAsync(
            "/api/v1/profiles/me/studio",
            new UpsertStudioProfileRequest(
                Height: 181m,
                Weight: 77m,
                BodyType: BodyType.Athletic,
                Gender: AvatarGender.Male,
                Muscularity: 72m,
                BodyFatPercentage: 14m,
                ChestCircumference: 101m,
                WaistCircumference: 83m,
                HipCircumference: 98m,
                ShoulderWidth: 46m,
                CalfCircumference: 38m,
                ArmLength: 62m,
                TorsoLength: 64m,
                LegLength: 108m,
                AutoChestCircumference: null,
                AutoWaistCircumference: null,
                AutoHipCircumference: null,
                AutoArmLength: null,
                AutoLegLength: null,
                GeneratedAvatar: null),
            JsonOptions);

        Assert.Equal(HttpStatusCode.OK, initialResponse.StatusCode);

        var enqueueResponse = await client.PostAsync(
            "/api/v1/profiles/me/studio/avatar-generation",
            content: null);

        Assert.Equal(HttpStatusCode.OK, enqueueResponse.StatusCode);

        var enqueuePayload = await enqueueResponse.Content.ReadFromJsonAsync<StudioAvatarGenerationStartResponse>();
        Assert.NotNull(enqueuePayload);

        var changedDraftResponse = await client.PutAsJsonAsync(
            "/api/v1/profiles/me/studio",
            new UpsertStudioProfileRequest(
                Height: 181m,
                Weight: 80m,
                BodyType: BodyType.Athletic,
                Gender: AvatarGender.Male,
                Muscularity: 72m,
                BodyFatPercentage: 14m,
                ChestCircumference: 101m,
                WaistCircumference: 83m,
                HipCircumference: 98m,
                ShoulderWidth: 46m,
                CalfCircumference: 38m,
                ArmLength: 62m,
                TorsoLength: 64m,
                LegLength: 108m,
                AutoChestCircumference: null,
                AutoWaistCircumference: null,
                AutoHipCircumference: null,
                AutoArmLength: null,
                AutoLegLength: null,
                GeneratedAvatar: null),
            JsonOptions);

        Assert.Equal(HttpStatusCode.OK, changedDraftResponse.StatusCode);

        var status = await client.GetFromJsonAsync<StudioAvatarGenerationStatusResponse>(
            $"/api/v1/profiles/me/studio/avatar-generation/{enqueuePayload!.TaskId}");

        Assert.NotNull(status);
        Assert.Equal("STALE", status!.Status);
        Assert.Equal(100, status.Progress);
        Assert.Null(status.Result);
        Assert.Contains("draft changed", status.Message, StringComparison.OrdinalIgnoreCase);

        var fetched = await client.GetFromJsonAsync<GetProfileResponse>("/api/v1/profiles/me");
        Assert.NotNull(fetched);
        Assert.Null(fetched!.GeneratedAvatar.ModelUrl);
        Assert.False(fetched.GeneratedAvatar.IsCurrent);
        Assert.Null(fetched.AutoMeasurements.WaistCircumference);
    }
}
