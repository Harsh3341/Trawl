using System.Collections.Concurrent;
using System.Net.Http.Json;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;
using Trawl.Gateway;

public class AskEventTests : IClassFixture<AskEventTests.Factory>
{
    private readonly Factory _factory;
    public AskEventTests(Factory f) => _factory = f;

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
    public sealed class SpyPublisher : IEventPublisher
    {
        public ConcurrentQueue<QueryAnsweredEvent> Events { get; } = new();
        public void PublishQueryAnswered(QueryAnsweredEvent evt) => Events.Enqueue(evt);
    }

    public class Factory : WebApplicationFactory<Program>
    {
        public SpyPublisher Spy { get; } = new();
        protected override void ConfigureWebHost(IWebHostBuilder builder)
        {
            Environment.SetEnvironmentVariable("JWT_SECRET", "test-secret-at-least-32-bytes-long-0000");
            Environment.SetEnvironmentVariable("GATEWAY_DB",
                "Host=localhost;Username=trawl;Password=trawl;Database=trawl_test");
            builder.ConfigureServices(s =>
            {
                s.RemoveAll<IEmbeddingClient>(); s.AddSingleton<IEmbeddingClient, FakeEmbedding>();
                s.RemoveAll<IChunkRepository>(); s.AddSingleton<IChunkRepository, FakeRepo>();
                s.RemoveAll<IEventPublisher>(); s.AddSingleton<IEventPublisher>(Spy);
            });
        }
    }

    [Fact]
    public async Task Ask_publishes_query_answered()
    {
        var client = _factory.CreateClient();
        var token = (await (await client.PostAsync("/token", null))
            .Content.ReadFromJsonAsync<TokenResp>())!.Token;
        client.DefaultRequestHeaders.Authorization = new("Bearer", token);

        var resp = await client.PostAsJsonAsync("/ask", new AskRequest("what changed?"));
        resp.EnsureSuccessStatusCode();

        Assert.True(_factory.Spy.Events.TryDequeue(out var evt));
        Assert.Equal("what changed?", evt!.Question);
        Assert.Equal("echo", evt.Provider);
        Assert.True(evt.Cited);
        Assert.Contains(1L, evt.RetrievedDocIds);
    }

    private record TokenResp(string Token);
}
