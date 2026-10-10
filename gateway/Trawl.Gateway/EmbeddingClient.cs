using System.Net.Http.Json;
namespace Trawl.Gateway;

public interface IEmbeddingClient
{
    Task<float[]> EmbedAsync(string text, CancellationToken ct = default);
}

public class HttpEmbeddingClient : IEmbeddingClient
{
    private readonly HttpClient _http;
    public HttpEmbeddingClient(HttpClient http) => _http = http;

    private record EmbedResponse(float[][] Vectors, int Dim);

    public async Task<float[]> EmbedAsync(string text, CancellationToken ct = default)
    {
        var resp = await _http.PostAsJsonAsync("/embed", new { texts = new[] { text } }, ct);
        resp.EnsureSuccessStatusCode();
        var body = await resp.Content.ReadFromJsonAsync<EmbedResponse>(cancellationToken: ct);
        return body!.Vectors[0];
    }
}
