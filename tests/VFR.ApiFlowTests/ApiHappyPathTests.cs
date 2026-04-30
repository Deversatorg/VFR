using System.Net;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text.Json;
using System.Text.Json.Serialization;
using ApplicationAuth.Features.Account.Login;
using ApplicationAuth.Features.Account.Register;
using VFR.ProfileApi.Domain;
using VFR.ProfileApi.Features.GetProfile;
using VFR.ProfileApi.Features.StudioAvatarGeneration;
using VFR.ProfileApi.Features.UpsertStudioProfile;
using Xunit;

namespace VFR.ApiFlowTests;

public sealed class ApiHappyPathTests : IClassFixture<ApplicationAuthFlowFactory>
{
    private static readonly JsonSerializerOptions JsonOptions = new(JsonSerializerDefaults.Web)
    {
        Converters = { new JsonStringEnumConverter() }
    };

    private readonly ApplicationAuthFlowFactory _authFactory;

    public ApiHappyPathTests(ApplicationAuthFlowFactory authFactory)
    {
        _authFactory = authFactory;
    }

    [Fact]
    public async Task RegisterLoginProfileAndAiEnqueue_HappyPath()
    {
        var email = $"{Guid.NewGuid():N}@example.com";
        var password = "Passw0rd1";

        using var authClient = _authFactory.CreateClient();

        var registerResponse = await authClient.PostAsJsonAsync("/api/v1/users", new RegisterRequest(
            Email: email,
            Password: password,
            ConfirmPassword: password));
        Assert.Equal(HttpStatusCode.Created, registerResponse.StatusCode);

        await _authFactory.ConfirmAndActivateUserAsync(email);

        var loginResponse = await authClient.PostAsJsonAsync("/api/v1/sessions", new LoginRequest(
            Email: email,
            Password: password,
            AccessTokenLifetime: null));
        Assert.Equal(HttpStatusCode.Created, loginResponse.StatusCode);

        var loginPayload = await loginResponse.Content.ReadFromJsonAsync<TestJsonEnvelope<LoginResponse>>();
        Assert.NotNull(loginPayload);

        var accessToken = loginPayload!.Data.Token.AccessToken;
        Assert.False(string.IsNullOrWhiteSpace(accessToken));

        var aiClient = new FakeAiEngineClient();
        using var profileFactory = new ProfileApiJwtFlowFactory(aiClient);
        using var profileClient = profileFactory.CreateClient();
        profileClient.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", accessToken);

        var notFoundResponse = await profileClient.GetAsync("/api/v1/profiles/me");
        Assert.Equal(HttpStatusCode.NotFound, notFoundResponse.StatusCode);

        var upsertResponse = await profileClient.PutAsJsonAsync(
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
                AutoChestCircumference: 100m,
                AutoWaistCircumference: 82m,
                AutoHipCircumference: 97m,
                AutoArmLength: 61m,
                AutoLegLength: 107m,
                GeneratedAvatar: null),
            JsonOptions);
        Assert.Equal(HttpStatusCode.OK, upsertResponse.StatusCode);

        var profile = await profileClient.GetFromJsonAsync<GetProfileResponse>("/api/v1/profiles/me");
        Assert.NotNull(profile);

        var enqueueResponse = await profileClient.PostAsync(
            "/api/v1/profiles/me/studio/avatar-generation",
            content: null);
        Assert.Equal(HttpStatusCode.OK, enqueueResponse.StatusCode);

        var enqueuePayload = await enqueueResponse.Content.ReadFromJsonAsync<StudioAvatarGenerationStartResponse>();
        Assert.NotNull(enqueuePayload);
        Assert.Equal("accepted", enqueuePayload!.Status);
        Assert.False(string.IsNullOrWhiteSpace(enqueuePayload.TaskId));

        Assert.NotNull(aiClient.LastProfile);
        Assert.Equal(profile.UserId, aiClient.LastProfile!.UserId);
        Assert.Equal(BodyType.Athletic, aiClient.LastProfile.BodyType);
        Assert.Equal(AvatarGender.Male, aiClient.LastProfile.Gender);
        Assert.Equal(181m, aiClient.LastProfile.Height);
        Assert.Equal(77m, aiClient.LastProfile.Weight);
        Assert.Equal(72m, aiClient.LastProfile.Muscularity);
        Assert.Equal(14m, aiClient.LastProfile.BodyFatPercentage);
        Assert.Equal(101m, aiClient.LastProfile.ChestCircumference);
        Assert.Equal(83m, aiClient.LastProfile.WaistCircumference);
        Assert.Equal(98m, aiClient.LastProfile.HipCircumference);
        Assert.Equal(46m, aiClient.LastProfile.ShoulderWidth);
        Assert.Equal(38m, aiClient.LastProfile.CalfCircumference);
        Assert.Equal(62m, aiClient.LastProfile.ArmLength);
        Assert.Equal(64m, aiClient.LastProfile.TorsoLength);
        Assert.Equal(108m, aiClient.LastProfile.LegLength);

        var status = await profileClient.GetFromJsonAsync<StudioAvatarGenerationStatusResponse>(
            $"/api/v1/profiles/me/studio/avatar-generation/{enqueuePayload.TaskId}");

        Assert.NotNull(status);
        Assert.Equal("SUCCESS", status!.Status);
        Assert.Equal("http://ai.test/models/generated-avatar.glb", status.Result!.Profile.GeneratedAvatar.ModelUrl);
        Assert.True(status.Result.Profile.GeneratedAvatar.IsCurrent);
    }
}
