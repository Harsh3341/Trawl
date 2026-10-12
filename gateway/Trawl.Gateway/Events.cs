using System.Text.Json;

namespace Trawl.Gateway;

public record QueryAnsweredEvent(
    string Question, int K, long LatencyMs, string Provider,
    IReadOnlyList<long> RetrievedDocIds, bool Cited, string Ts);

public interface IEventPublisher
{
    void PublishQueryAnswered(QueryAnsweredEvent evt);
}

// Default: analytics emission must never block /ask, and tests stay broker-free.
public sealed class NoOpEventPublisher : IEventPublisher
{
    public void PublishQueryAnswered(QueryAnsweredEvent evt) { }
}

public static class EventJson
{
    private static readonly JsonSerializerOptions Opts =
        new() { PropertyNamingPolicy = JsonNamingPolicy.CamelCase };

    public static string Serialize<T>(T evt) => JsonSerializer.Serialize(evt, Opts);
}
