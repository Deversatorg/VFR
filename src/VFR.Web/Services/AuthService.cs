namespace VFR.Web.Services;

/// <summary>
/// In-memory JWT token store. Holds access + refresh tokens for the session.
/// In production, replace with a secure storage strategy (e.g. HttpOnly cookie via BFF).
/// </summary>
public class AuthService
{
    private string? _accessToken;
    private string? _refreshToken;
    private string? _userEmail;

    public bool IsAuthenticated => !string.IsNullOrEmpty(_accessToken);
    public string? UserEmail => _userEmail;

    public event Action? OnAuthStateChanged;

    public void SetTokens(string accessToken, string refreshToken, string email)
    {
        _accessToken  = accessToken;
        _refreshToken = refreshToken;
        _userEmail    = email;
        OnAuthStateChanged?.Invoke();
    }

    public void Clear()
    {
        _accessToken  = null;
        _refreshToken = null;
        _userEmail    = null;
        OnAuthStateChanged?.Invoke();
    }

    /// <summary>Returns the Bearer authorization header value, or null if not authenticated.</summary>
    public string? GetBearerHeader() =>
        _accessToken is null ? null : $"Bearer {_accessToken}";
}
