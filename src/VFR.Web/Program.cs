using Microsoft.AspNetCore.Components.Web;
using Microsoft.AspNetCore.Components.WebAssembly.Hosting;
using VFR.Web;
using VFR.Web.Services;

var builder = WebAssemblyHostBuilder.CreateDefault(args);
builder.RootComponents.Add<App>("#app");
builder.RootComponents.Add<HeadOutlet>("head::after");

// ── Base address resolution (Aspire injects via window.env or appsettings) ──
var baseAddress = builder.Configuration["ApiBaseUrl"] ?? builder.HostEnvironment.BaseAddress;

// ── Auth Service (in-memory JWT store) ──────────────────────────────────────
builder.Services.AddSingleton<AuthService>();

// ── Typed HTTP Clients ────────────────────────────────────────────────────────
builder.Services.AddHttpClient<AuthApiClient>(client =>
{
    client.BaseAddress = new Uri(builder.Configuration["AuthApiUrl"] ?? "http://localhost:5001");
});

builder.Services.AddHttpClient<ProfileApiClient>(client =>
{
    client.BaseAddress = new Uri(builder.Configuration["ProfileApiUrl"] ?? "http://localhost:5002");
});

// ── Semantic Kernel AI Size Advisor ────────────────────────────────────────
builder.Services.AddSingleton<SizeAdvisorService>();

await builder.Build().RunAsync();
