namespace VFR.Web.Services;

/// <summary>
/// AI Size Advisor — placeholder for future Gemini integration.
/// TODO Phase 5: Replace with Google Gemini API (generativelanguage.googleapis.com)
///   using HttpClient + streaming to call gemini-2.0-flash or gemini-pro.
///   System prompt advises on clothing sizes based on user body measurements.
/// </summary>
public class SizeAdvisorService
{
    // Not yet implemented — will use Gemini API
    public bool IsAvailable => false;

    public async IAsyncEnumerable<string> AskAsync(
        string userMessage,
        string? measurementContext = null,
        [System.Runtime.CompilerServices.EnumeratorCancellation] CancellationToken ct = default)
    {
        // TODO: call Gemini API here
        yield return "🔮 AI Size Advisor powered by Gemini — coming soon!";
        await Task.CompletedTask;
    }

    public void ResetHistory() { }
}
