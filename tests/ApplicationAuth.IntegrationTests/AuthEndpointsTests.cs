using System.Net;
using System.Net.Http.Json;
using ApplicationAuth.DAL;
using ApplicationAuth.Domain.Entities.Identity;
using ApplicationAuth.Features.Account.Login;
using ApplicationAuth.Features.Account.Register;
using Microsoft.Extensions.DependencyInjection;
using Xunit;

namespace ApplicationAuth.IntegrationTests;

public sealed class AuthEndpointsTests : IClassFixture<ApplicationAuthWebApplicationFactory>
{
    private readonly ApplicationAuthWebApplicationFactory _factory;
    private readonly HttpClient _client;

    public AuthEndpointsTests(ApplicationAuthWebApplicationFactory factory)
    {
        _factory = factory;
        _client = factory.CreateClient();
    }

    [Fact]
    public async Task Register_CreatesUserAndVerificationToken()
    {
        var email = $"{Guid.NewGuid():N}@example.com";

        var response = await _client.PostAsJsonAsync("/api/v1/users", new RegisterRequest(
            Email: email,
            Password: "Passw0rd1",
            ConfirmPassword: "Passw0rd1"));

        Assert.Equal(HttpStatusCode.Created, response.StatusCode);

        var payload = await response.Content.ReadFromJsonAsync<TestJsonEnvelope<RegisterResponse>>();
        Assert.NotNull(payload);
        Assert.Equal(email, payload!.Data.Email);

        using var scope = _factory.Services.CreateScope();
        var db = scope.ServiceProvider.GetRequiredService<DataContext>();

        var user = db.Set<ApplicationUser>().SingleOrDefault(x => x.Email == email);
        Assert.NotNull(user);
        Assert.False(user!.EmailConfirmed);

        var tokens = db.Set<VerificationToken>().Where(x => x.UserId == user.Id).ToList();
        Assert.Single(tokens);
    }

    [Fact]
    public async Task Login_ReturnsBearerTokenAfterConfirmation()
    {
        var email = $"{Guid.NewGuid():N}@example.com";

        var registerResponse = await _client.PostAsJsonAsync("/api/v1/users", new RegisterRequest(
            Email: email,
            Password: "Passw0rd1",
            ConfirmPassword: "Passw0rd1"));
        Assert.Equal(HttpStatusCode.Created, registerResponse.StatusCode);

        await _factory.ConfirmAndActivateUserAsync(email);

        var response = await _client.PostAsJsonAsync("/api/v1/sessions", new LoginRequest(
            Email: email,
            Password: "Passw0rd1",
            AccessTokenLifetime: null));

        Assert.Equal(HttpStatusCode.Created, response.StatusCode);

        var payload = await response.Content.ReadFromJsonAsync<TestJsonEnvelope<LoginResponse>>();
        Assert.NotNull(payload);
        Assert.False(string.IsNullOrWhiteSpace(payload!.Data.Token.AccessToken));
        Assert.False(string.IsNullOrWhiteSpace(payload.Data.Token.RefreshToken));
        Assert.Equal("Bearer", payload.Data.Token.Type);
        Assert.Equal(email, payload.Data.User.Email);
    }
}
