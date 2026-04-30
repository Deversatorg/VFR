using System.Net;
using System.Text;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging.Abstractions;
using VFR.ProfileApi.Domain;
using VFR.ProfileApi.Features.StudioAvatarGeneration;
using Xunit;

namespace VFR.ProfileApi.IntegrationTests;

public sealed class AiEngineClientTests
{
    [Fact]
    public async Task EnqueueProfileAvatarAsync_SendsSnakeCasePayload()
    {
        HttpRequestMessage? capturedRequest = null;
        string? capturedBody = null;
        using var httpClient = new HttpClient(new StubHttpMessageHandler(async (request, _) =>
        {
            capturedRequest = request;
            capturedBody = await request.Content!.ReadAsStringAsync();
            return JsonResponse(HttpStatusCode.OK, """
                {"task_id":"task-1","status":"accepted","message":"queued"}
                """);
        }));

        var client = CreateClient(httpClient);

        var response = await client.EnqueueProfileAvatarAsync(
            new PhysicalProfile
            {
                UserId = "user-1",
                Height = 181m,
                Weight = 77m,
                BodyType = BodyType.Athletic,
                Gender = AvatarGender.Male,
                BodyFatPercentage = 14m,
                ArmLength = 62m,
                LegLength = 108m,
            },
            CancellationToken.None);

        Assert.Equal("task-1", response.TaskId);
        Assert.Equal(HttpMethod.Post, capturedRequest!.Method);
        Assert.Equal("/api/v1/avatar/generate-from-profile", capturedRequest.RequestUri!.AbsolutePath);
        Assert.Contains("\"user_id\":\"user-1\"", capturedBody);
        Assert.Contains("\"body_fat_percentage\":14", capturedBody);
        Assert.Contains("\"arm_length\":62", capturedBody);
        Assert.Contains("\"face_image_url\":\"\"", capturedBody);
        Assert.DoesNotContain("userId", capturedBody);
    }

    [Fact]
    public void NormalizeModelUrl_UsesPublicBaseUrlForServedModels()
    {
        using var httpClient = new HttpClient(new StubHttpMessageHandler((_, _) => JsonResponse(HttpStatusCode.OK, "{}")));
        var client = CreateClient(
            httpClient,
            new Dictionary<string, string?>
            {
                ["AiEngine:BaseUrl"] = "http://ai.internal",
                ["AiEngine:PublicBaseUrl"] = "https://ai.public.example",
            });

        var modelUrl = client.NormalizeModelUrl("/models/generated-avatar.glb");

        Assert.Equal("https://ai.public.example/models/generated-avatar.glb", modelUrl);
    }

    [Fact]
    public void NormalizeModelUrl_RejectsNonFetchableSuccessArtifactPath()
    {
        using var httpClient = new HttpClient(new StubHttpMessageHandler((_, _) => JsonResponse(HttpStatusCode.OK, "{}")));
        var client = CreateClient(httpClient);

        Assert.Null(client.NormalizeModelUrl("/tmp/generated-avatar.glb"));
        Assert.Null(client.NormalizeModelUrl("C:\\temp\\generated-avatar.glb"));
    }

    [Fact]
    public async Task GetAvatarStatusAsync_ThrowsOnAiHttpFailure()
    {
        using var httpClient = new HttpClient(new StubHttpMessageHandler((_, _) =>
            JsonResponse(HttpStatusCode.BadGateway, "upstream failed")));
        var client = CreateClient(httpClient);

        await Assert.ThrowsAsync<HttpRequestException>(() =>
            client.GetAvatarStatusAsync("task-1", CancellationToken.None));
    }

    private static AiEngineClient CreateClient(
        HttpClient httpClient,
        Dictionary<string, string?>? values = null)
    {
        var configuration = new ConfigurationBuilder()
            .AddInMemoryCollection(values ?? new Dictionary<string, string?>
            {
                ["AiEngine:BaseUrl"] = "http://ai.internal",
            })
            .Build();

        return new AiEngineClient(httpClient, configuration, NullLogger<AiEngineClient>.Instance);
    }

    private static HttpResponseMessage JsonResponse(HttpStatusCode statusCode, string content) =>
        new(statusCode)
        {
            Content = new StringContent(content, Encoding.UTF8, "application/json"),
        };

    private sealed class StubHttpMessageHandler(
        Func<HttpRequestMessage, CancellationToken, Task<HttpResponseMessage>> handler
    ) : HttpMessageHandler
    {
        public StubHttpMessageHandler(Func<HttpRequestMessage, CancellationToken, HttpResponseMessage> handler)
            : this((request, ct) => Task.FromResult(handler(request, ct)))
        {
        }

        protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken) =>
            handler(request, cancellationToken);
    }
}
