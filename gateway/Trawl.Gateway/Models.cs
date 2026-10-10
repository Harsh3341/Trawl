namespace Trawl.Gateway;

public record AskRequest(string Question, int K = 5);
public record Citation(long DocumentId, string Url, string Title, string? Version);
public record AskResponse(string Answer, IReadOnlyList<Citation> Citations, long LatencyMs);

public record RetrievedChunk(
    long DocumentId, string Url, string Title, string? Version, string Text, double Score);
