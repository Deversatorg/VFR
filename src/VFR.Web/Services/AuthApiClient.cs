using System.Net.Http.Json;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace VFR.Web.Services;

public record LoginRequest(string Login, string Password);
public record RegisterRequest(string Email, string UserName, string Password, string ConfirmPassword);
public record LoginResponse(string AccessToken, string RefreshToken);
public record RegisterResponse(bool Succeeded, string? Message);

/// <summary>
/// Typed HTTP client for the ApplicationAuth service endpoints.
/// Uses the same request/response contracts as ApplicationAuth's Minimal API feature slices.
/// </summary>
public class AuthApiClient
{
    private readonly HttpClient _http;
    private readonly AuthService _auth;

    public AuthApiClient(HttpClient http, AuthService auth)
    {
        _http = http;
        _auth = auth;
    }

    public async Task<(bool Success, string? Error)> LoginAsync(string email, string password)
    {
        var response = await _http.PostAsJsonAsync("/api/v1/account/login",
            new LoginRequest(email, password));

        if (!response.IsSuccessStatusCode)
        {
            var problem = await response.Content.ReadAsStringAsync();
            return (false, problem);
        }

        var result = await response.Content.ReadFromJsonAsync<LoginResponse>();
        if (result is null) return (false, "Invalid server response.");

        _auth.SetTokens(result.AccessToken, result.RefreshToken, email);
        return (true, null);
    }

    public async Task<(bool Success, string? Error)> RegisterAsync(
        string email, string userName, string password, string confirmPassword)
    {
        var response = await _http.PostAsJsonAsync("/api/v1/account/register",
            new RegisterRequest(email, userName, password, confirmPassword));

        if (!response.IsSuccessStatusCode)
        {
            var problem = await response.Content.ReadAsStringAsync();
            return (false, problem);
        }

        return (true, null);
    }

    public void Logout() => _auth.Clear();
}
