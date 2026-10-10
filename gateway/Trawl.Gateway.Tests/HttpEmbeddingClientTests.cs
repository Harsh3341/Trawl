using System.Net;
using System.Text;
using Trawl.Gateway;

public class HttpEmbeddingClientTests
{
    private sealed class StubHandler : HttpMessageHandler
    {
        protected override Task<HttpResponseMessage> SendAsync(
            HttpRequestMessage request, CancellationToken ct) =>
            Task.FromResult(new HttpResponseMessage(HttpStatusCode.OK)
            {
                Content = new StringContent("{\"vectors\":[[0.5,0.25]],\"dim\":2}",
                                            Encoding.UTF8, "application/json")
            });
    }

    [Fact]
    public async Task Embed_returns_first_vector()
    {
        var http = new HttpClient(new StubHandler()) { BaseAddress = new Uri("http://emb") };
        var vec = await new HttpEmbeddingClient(http).EmbedAsync("hello");
        Assert.Equal(new[] { 0.5f, 0.25f }, vec);
    }
}
