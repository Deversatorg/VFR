using System.Text.Json.Serialization;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.TestHost;
using Microsoft.Extensions.DependencyInjection;

namespace VFR.ApiFlowTests;

public sealed class AiEnqueueTestServer : IDisposable
{
    private readonly TestServer _server;

    public AiEnqueueTestServer()
    {
        var builder = new WebHostBuilder()
            .ConfigureServices(services => services.AddRouting())
            .Configure(app =>
            {
                app.UseRouting();
                app.UseEndpoints(endpoints =>
                {
                    endpoints.MapPost("/api/v1/avatar/generate-from-profile", async context =>
                    {
                        LastRequest = await context.Request.ReadFromJsonAsync<ProfileAvatarEnqueueRequest>();

                        var response = new AvatarEnqueueAcceptedResponse(
                            TaskId: $"queued-{Guid.NewGuid():N}",
                            Status: "accepted",
                            Message: "Parametric avatar generation task queued.");

                        await context.Response.WriteAsJsonAsync(response);
                    });
                });
            });

        _server = new TestServer(builder);
        Client = _server.CreateClient();
    }

    public HttpClient Client { get; }

    public ProfileAvatarEnqueueRequest? LastRequest { get; private set; }

    public void Dispose()
    {
        Client.Dispose();
        _server.Dispose();
    }
}

public sealed record ProfileAvatarEnqueueRequest(
    [property: JsonPropertyName("user_id")] string UserId,
    [property: JsonPropertyName("height")] double Height,
    [property: JsonPropertyName("weight")] double Weight,
    [property: JsonPropertyName("body_type")] string BodyType,
    [property: JsonPropertyName("gender")] string Gender,
    [property: JsonPropertyName("muscularity")] double Muscularity,
    [property: JsonPropertyName("body_fat_percentage")] double BodyFatPercentage,
    [property: JsonPropertyName("chest")] double Chest,
    [property: JsonPropertyName("waist")] double Waist,
    [property: JsonPropertyName("hip")] double Hip,
    [property: JsonPropertyName("shoulder")] double Shoulder,
    [property: JsonPropertyName("calf")] double Calf,
    [property: JsonPropertyName("arm_length")] double ArmLength,
    [property: JsonPropertyName("torso_length")] double TorsoLength,
    [property: JsonPropertyName("leg_length")] double LegLength,
    [property: JsonPropertyName("face_image_url")] string FaceImageUrl
);

public sealed record AvatarEnqueueAcceptedResponse(
    [property: JsonPropertyName("task_id")] string TaskId,
    [property: JsonPropertyName("status")] string Status,
    [property: JsonPropertyName("message")] string Message
);
