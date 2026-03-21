using System.Text.Json.Serialization;

namespace VFR.ApiFlowTests;

public sealed record TestJsonEnvelope<T>(
    [property: JsonPropertyName("_v")] string Version,
    [property: JsonPropertyName("data")] T Data
);
