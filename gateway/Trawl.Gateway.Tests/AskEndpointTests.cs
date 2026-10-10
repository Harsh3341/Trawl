using System.Net;
using System.Net.Http.Json;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;
using Trawl.Gateway;

public class AskEndpointTests : IClassFixture<AskEndpointTests.Factory>
{
    private readonly Factory _factory;
    public AskEndpointTests(Factory f) => _factory = f;

    private sealed class FakeEmbedding : IEmbeddingClient
    {
        public Task<float[]> EmbedAsync(string t, CancellationToken ct = default) =>
            Task.FromResult(new float[768]);
    }
    private sealed class FakeRepo : IChunkRepository
    {
        public Task<IReadOnlyList<RetrievedChunk>> SearchAsync(float[] e, int k, CancellationToken ct = default) =>
            Task.FromResult<IReadOnlyList<RetrievedChunk>>(new List<RetrievedChunk>
            { new(1, "https://x/1", "v2.0.0", "v2.0.0", "Added dark mode.", 0.9) });
    }

    public class Factory : WebApplicationFactory<Program>
    {
        protected override void ConfigureWebHost(IWebHostBuilder builder)
        {
            Environment.SetEnvironmentVariable("JWT_SECRET", "test-secret-at-least-32-bytes-long-0000");
            Environment.SetEnvironmentVariable("GATEWAY_DB",
                "Host=localhost;Username=trawl;Password=trawl;Database=trawl_test");
            builder.ConfigureServices(s =>
            {
                s.RemoveAll<IEmbeddingClient>(); s.AddSingleton<IEmbeddingClient, FakeEmbedding>();
                s.RemoveAll<IChunkRepository>(); s.AddSingleton<IChunkRepository, FakeRepo>();
            });
        }
    }

    [Fact]
    public async Task Ask_without_token_is_unauthorized()
    {
        var resp = await _factory.CreateClient()
            .PostAsJsonAsync("/ask", new AskRequest("what changed?"));
        Assert.Equal(HttpStatusCode.Unauthorized, resp.StatusCode);
    }

    [Fact]
    public async Task Ask_with_token_returns_cited_answer()
    {
        var client = _factory.CreateClient();
        var token = (await (await client.PostAsync("/token", null))
            .Content.ReadFromJsonAsync<TokenResp>())!.Token;
        client.DefaultRequestHeaders.Authorization = new("Bearer", token);

        var resp = await client.PostAsJsonAsync("/ask", new AskRequest("what changed?"));
        Assert.Equal(HttpStatusCode.OK, resp.StatusCode);
        var body = await resp.Content.ReadFromJsonAsync<AskResponse>();
        Assert.Contains("dark mode", body!.Answer);
        Assert.Single(body.Citations);
        Assert.Equal(1, body.Citations[0].DocumentId);
    }

    private record TokenResp(string Token);
}
