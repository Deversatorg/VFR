using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Diagnostics.HealthChecks;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Diagnostics.HealthChecks;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.ServiceDiscovery;
using OpenTelemetry;
using OpenTelemetry.Metrics;
using OpenTelemetry.Resources;
using OpenTelemetry.Trace;
using System.Diagnostics;
using System.Reflection;

namespace Microsoft.Extensions.Hosting;

// Adds common .NET Aspire services: service discovery, resilience, health checks, and OpenTelemetry.
// This project should be referenced by each service project in your solution.
// To learn more about using this project, see https://aka.ms/dotnet/aspire/service-defaults
public static class Extensions
{
    public static IHostApplicationBuilder AddServiceDefaults(this IHostApplicationBuilder builder)
    {
        builder.ConfigureLoggingDefaults();
        builder.ConfigureOpenTelemetry();

        builder.AddDefaultHealthChecks();

        builder.Services.AddServiceDiscovery();

        builder.Services.ConfigureHttpClientDefaults(http =>
        {
            // Turn on resilience by default
            http.AddStandardResilienceHandler();

            // Turn on service discovery by default
            http.AddServiceDiscovery();
        });

        // Uncomment the following to restrict the allowed schemes for service discovery.
        // builder.Services.Configure<ServiceDiscoveryOptions>(options =>
        // {
        //     options.AllowedSchemes = ["https"];
        // });

        return builder;
    }

    private static IHostApplicationBuilder ConfigureLoggingDefaults(this IHostApplicationBuilder builder)
    {
        Activity.DefaultIdFormat = ActivityIdFormat.W3C;
        Activity.ForceDefaultIdFormat = true;

        builder.Logging.ClearProviders();
        builder.Logging.AddFilter("LuckyPennySoftware.MediatR", LogLevel.None);
        builder.Logging.Configure(options =>
        {
            options.ActivityTrackingOptions =
                ActivityTrackingOptions.SpanId |
                ActivityTrackingOptions.TraceId |
                ActivityTrackingOptions.ParentId;
        });
        builder.Logging.AddJsonConsole(options =>
        {
            options.IncludeScopes = true;
            options.TimestampFormat = "O";
        });

        return builder;
    }

    public static IHostApplicationBuilder ConfigureOpenTelemetry(this IHostApplicationBuilder builder)
    {
        builder.Logging.AddOpenTelemetry(logging =>
        {
            logging.IncludeFormattedMessage = true;
            logging.IncludeScopes = true;
            logging.ParseStateValues = true;
        });

        builder.Services.AddOpenTelemetry()
            .ConfigureResource(resource =>
            {
                resource.AddService(
                    serviceName: GetServiceName(builder.Environment, builder.Configuration),
                    serviceVersion: GetServiceVersion(),
                    serviceNamespace: GetServiceNamespace(builder.Configuration));

                resource.AddAttributes(new Dictionary<string, object>
                {
                    ["deployment.environment"] = builder.Environment.EnvironmentName,
                });
            })
            .WithMetrics(metrics =>
            {
                metrics.AddAspNetCoreInstrumentation()
                    .AddHttpClientInstrumentation()
                    .AddRuntimeInstrumentation();
            })
            .WithTracing(tracing =>
            {
                tracing.AddAspNetCoreInstrumentation()
                    // Uncomment the following line to enable gRPC instrumentation (requires the OpenTelemetry.Instrumentation.GrpcNetClient package)
                    //.AddGrpcClientInstrumentation()
                    .AddHttpClientInstrumentation();
            });

        builder.AddOpenTelemetryExporters();

        return builder;
    }

    private static IHostApplicationBuilder AddOpenTelemetryExporters(this IHostApplicationBuilder builder)
    {
        var useOtlpExporter = !string.IsNullOrWhiteSpace(builder.Configuration["OTEL_EXPORTER_OTLP_ENDPOINT"]);

        if (useOtlpExporter)
        {
            builder.Services.AddOpenTelemetry().UseOtlpExporter();
        }

        // Uncomment the following lines to enable the Azure Monitor exporter (requires the Azure.Monitor.OpenTelemetry.AspNetCore package)
        //if (!string.IsNullOrEmpty(builder.Configuration["APPLICATIONINSIGHTS_CONNECTION_STRING"]))
        //{
        //    builder.Services.AddOpenTelemetry()
        //       .UseAzureMonitor();
        //}

        return builder;
    }

    public static IHostApplicationBuilder AddDefaultHealthChecks(this IHostApplicationBuilder builder)
    {
        builder.Services.AddHealthChecks()
            // Add a default liveness check to ensure app is responsive
            .AddCheck("self", () => HealthCheckResult.Healthy(), ["live"]);

        return builder;
    }

    public static WebApplication UseDefaultRequestLogging(this WebApplication app)
    {
        app.Use(async (context, next) =>
        {
            ApplyRequestIdentifier(context);

            if (IsHealthCheckPath(context.Request.Path))
            {
                await next();
                return;
            }

            var logger = context.RequestServices.GetRequiredService<ILoggerFactory>()
                .CreateLogger("VFR.Request");
            var startedAt = Stopwatch.GetTimestamp();

            try
            {
                await next();
            }
            catch (Exception ex)
            {
                LogRequestCompletion(logger, context, startedAt, ex);
                throw;
            }

            LogRequestCompletion(logger, context, startedAt, exception: null);
        });

        return app;
    }

    public static WebApplication MapDefaultEndpoints(this WebApplication app)
    {
        // Adding health checks endpoints to applications in non-development environments has security implications.
        // See https://aka.ms/dotnet/aspire/healthchecks for details before enabling these endpoints in non-development environments.
        if (app.Environment.IsDevelopment())
        {
            // All health checks must pass for app to be considered ready to accept traffic after starting
            app.MapHealthChecks("/health");

            // Only health checks tagged with the "live" tag must pass for app to be considered alive
            app.MapHealthChecks("/alive", new HealthCheckOptions
            {
                Predicate = r => r.Tags.Contains("live")
            });
        }

        return app;
    }

    private static void ApplyRequestIdentifier(HttpContext context)
    {
        var incomingRequestId = context.Request.Headers["X-Request-ID"].FirstOrDefault();
        if (!string.IsNullOrWhiteSpace(incomingRequestId) && incomingRequestId.Length <= 128)
        {
            context.TraceIdentifier = incomingRequestId;
        }

        context.Response.Headers["X-Request-ID"] = context.TraceIdentifier;
    }

    private static void LogRequestCompletion(
        ILogger logger,
        HttpContext context,
        long startedAt,
        Exception? exception)
    {
        var elapsed = Stopwatch.GetElapsedTime(startedAt).TotalMilliseconds;
        var traceId = Activity.Current?.TraceId.ToString();
        var spanId = Activity.Current?.SpanId.ToString();
        var statusCode = exception is null ? context.Response.StatusCode : StatusCodes.Status500InternalServerError;
        var logLevel = GetRequestLogLevel(statusCode, exception);

        using var _ = logger.BeginScope(new Dictionary<string, object?>
        {
            ["request_id"] = context.TraceIdentifier,
            ["trace_id"] = string.IsNullOrWhiteSpace(traceId) ? null : traceId,
            ["span_id"] = string.IsNullOrWhiteSpace(spanId) ? null : spanId,
            ["http.method"] = context.Request.Method,
            ["http.path"] = context.Request.Path.Value,
        });

        logger.Log(
            logLevel,
            exception,
            "HTTP {Method} {Path} responded {StatusCode} in {ElapsedMs} ms",
            context.Request.Method,
            context.Request.Path.Value,
            statusCode,
            Math.Round(elapsed, 2));
    }

    private static bool IsHealthCheckPath(PathString path) =>
        path.Equals("/health", StringComparison.OrdinalIgnoreCase)
        || path.Equals("/alive", StringComparison.OrdinalIgnoreCase);

    private static LogLevel GetRequestLogLevel(int statusCode, Exception? exception)
    {
        if (exception is not null || statusCode >= StatusCodes.Status500InternalServerError)
        {
            return LogLevel.Error;
        }

        return statusCode switch
        {
            StatusCodes.Status400BadRequest => LogLevel.Information,
            StatusCodes.Status401Unauthorized => LogLevel.Information,
            StatusCodes.Status403Forbidden => LogLevel.Information,
            StatusCodes.Status404NotFound => LogLevel.Information,
            StatusCodes.Status429TooManyRequests => LogLevel.Warning,
            >= StatusCodes.Status400BadRequest => LogLevel.Warning,
            _ => LogLevel.Information,
        };
    }

    private static string GetServiceName(IHostEnvironment environment, IConfiguration configuration) =>
        configuration["OTEL_SERVICE_NAME"]?.Trim()
        ?? environment.ApplicationName;

    private static string GetServiceNamespace(IConfiguration configuration) =>
        configuration["OTEL_SERVICE_NAMESPACE"]?.Trim() ?? "virtual-fitting-room";

    private static string GetServiceVersion()
    {
        var entryAssembly = Assembly.GetEntryAssembly();
        var informationalVersion = entryAssembly?
            .GetCustomAttribute<AssemblyInformationalVersionAttribute>()?
            .InformationalVersion;

        if (!string.IsNullOrWhiteSpace(informationalVersion))
        {
            return informationalVersion;
        }

        return entryAssembly?.GetName().Version?.ToString() ?? "unknown";
    }
}
