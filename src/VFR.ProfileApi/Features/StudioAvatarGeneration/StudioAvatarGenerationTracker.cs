using System.Collections.Concurrent;
using System.Text.Json;
using StackExchange.Redis;

namespace VFR.ProfileApi.Features.StudioAvatarGeneration;

public interface IStudioAvatarGenerationTracker
{
    Task RegisterAsync(StudioAvatarGenerationTask task, CancellationToken ct);
    Task<StudioAvatarGenerationTask?> GetAsync(string taskId, CancellationToken ct);
}

public sealed record StudioAvatarGenerationTask(
    string TaskId,
    string UserId,
    string DraftStateHash,
    DateTime CreatedAt
);

public sealed class InMemoryStudioAvatarGenerationTracker : IStudioAvatarGenerationTracker
{
    private readonly ConcurrentDictionary<string, StudioAvatarGenerationTask> tasks = new(StringComparer.Ordinal);

    public Task RegisterAsync(StudioAvatarGenerationTask task, CancellationToken ct)
    {
        tasks[task.TaskId] = task;
        return Task.CompletedTask;
    }

    public Task<StudioAvatarGenerationTask?> GetAsync(string taskId, CancellationToken ct) =>
        Task.FromResult(tasks.TryGetValue(taskId, out var task) ? task : null);
}

public sealed class RedisStudioAvatarGenerationTracker(IConnectionMultiplexer redis) : IStudioAvatarGenerationTracker
{
    private static readonly TimeSpan TaskTtl = TimeSpan.FromHours(2);
    private static readonly JsonSerializerOptions JsonOptions = new(JsonSerializerDefaults.Web);
    private readonly IDatabase database = redis.GetDatabase();

    public async Task RegisterAsync(StudioAvatarGenerationTask task, CancellationToken ct)
    {
        ct.ThrowIfCancellationRequested();
        await database.StringSetAsync(Key(task.TaskId), JsonSerializer.Serialize(task, JsonOptions), TaskTtl);
    }

    public async Task<StudioAvatarGenerationTask?> GetAsync(string taskId, CancellationToken ct)
    {
        ct.ThrowIfCancellationRequested();
        var value = await database.StringGetAsync(Key(taskId));
        return value.HasValue
            ? JsonSerializer.Deserialize<StudioAvatarGenerationTask>(value.ToString(), JsonOptions)
            : null;
    }

    private static string Key(string taskId) => $"studio-avatar-generation:{taskId}";
}
