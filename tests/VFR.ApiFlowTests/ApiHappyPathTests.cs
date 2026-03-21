using System.Net;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text.Json;
using System.Text.Json.Serialization;
using ApplicationAuth.Features.Account.Login;
using ApplicationAuth.Features.Account.Register;
using VFR.ProfileApi.Domain;
using VFR.ProfileApi.Features.GetProfile;
using VFR.ProfileApi.Features.UpsertStudioProfile;
using Xunit;

namespace VFR.ApiFlowTests;

public sealed class ApiHappyPathTests : IClassFixture<ApplicationAuthFlowFactory>, IClassFixture<ProfileApiJwtFlowFactory>
{
    private static readonly JsonSerializerOptions JsonOptions = new(JsonSerializerDefaults.Web)
    {
        Converters = { new JsonStringEnumConverter() }
    };

    private readonly ApplicationAuthFlowFactory _authFactory;
    private readonly ProfileApiJwtFlowFactory _profileFactory;

    public ApiHappyPathTests(ApplicationAuthFlowFactory authFactory, ProfileApiJwtFlowFactory profileFactory)
    {
        _authFactory = authFactory;
        _profileFactory = profileFactory;
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

        using var profileClient = _profileFactory.CreateClient();
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

        using var aiServer = new AiEnqueueTestServer();
        var enqueueRequest = CreateAiRequest(profile!);

        var aiResponse = await aiServer.Client.PostAsJsonAsync(
            "/api/v1/avatar/generate-from-profile",
            enqueueRequest,
            JsonOptions);
        Assert.Equal(HttpStatusCode.OK, aiResponse.StatusCode);

        var aiPayload = await aiResponse.Content.ReadFromJsonAsync<AvatarEnqueueAcceptedResponse>();
        Assert.NotNull(aiPayload);
        Assert.Equal("accepted", aiPayload!.Status);
        Assert.Equal("Parametric avatar generation task queued.", aiPayload.Message);
        Assert.False(string.IsNullOrWhiteSpace(aiPayload.TaskId));

        Assert.NotNull(aiServer.LastRequest);
        Assert.Equal(profile.UserId, aiServer.LastRequest!.UserId);
        Assert.Equal("athletic", aiServer.LastRequest.BodyType);
        Assert.Equal("male", aiServer.LastRequest.Gender);
        Assert.Equal(181d, aiServer.LastRequest.Height);
        Assert.Equal(77d, aiServer.LastRequest.Weight);
        Assert.Equal(72d, aiServer.LastRequest.Muscularity);
        Assert.Equal(14d, aiServer.LastRequest.BodyFatPercentage);
        Assert.Equal(101d, aiServer.LastRequest.Chest);
        Assert.Equal(83d, aiServer.LastRequest.Waist);
        Assert.Equal(98d, aiServer.LastRequest.Hip);
        Assert.Equal(46d, aiServer.LastRequest.Shoulder);
        Assert.Equal(38d, aiServer.LastRequest.Calf);
        Assert.Equal(62d, aiServer.LastRequest.ArmLength);
        Assert.Equal(64d, aiServer.LastRequest.TorsoLength);
        Assert.Equal(108d, aiServer.LastRequest.LegLength);
        Assert.Equal(string.Empty, aiServer.LastRequest.FaceImageUrl);
    }

    private static ProfileAvatarEnqueueRequest CreateAiRequest(GetProfileResponse profile) =>
        new(
            UserId: profile.UserId,
            Height: profile.Height,
            Weight: profile.Weight,
            BodyType: profile.BodyType.ToLowerInvariant(),
            Gender: profile.Gender.ToLowerInvariant(),
            Muscularity: profile.Muscularity ?? 0,
            BodyFatPercentage: profile.BodyFatPercentage ?? 0,
            Chest: profile.ManualMeasurements.ChestCircumference ?? 0,
            Waist: profile.ManualMeasurements.WaistCircumference ?? 0,
            Hip: profile.ManualMeasurements.HipCircumference ?? 0,
            Shoulder: profile.ManualMeasurements.ShoulderWidth ?? 0,
            Calf: profile.ManualMeasurements.CalfCircumference ?? 0,
            ArmLength: profile.ManualMeasurements.ArmLength ?? 0,
            TorsoLength: profile.ManualMeasurements.TorsoLength ?? 0,
            LegLength: profile.ManualMeasurements.LegLength ?? 0,
            FaceImageUrl: string.Empty);
}
