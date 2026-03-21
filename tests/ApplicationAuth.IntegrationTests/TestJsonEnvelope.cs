using System.Text.Json.Serialization;

namespace ApplicationAuth.IntegrationTests;

public sealed record TestJsonEnvelope<T>(
    [property: JsonPropertyName("_v")] string Version,
    [property: JsonPropertyName("data")] T Data
);
