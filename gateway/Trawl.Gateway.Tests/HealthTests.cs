using System.Net;
using Microsoft.AspNetCore.Mvc.Testing;

public class HealthTests : IClassFixture<WebApplicationFactory<Program>>
{
    private readonly WebApplicationFactory<Program> _factory;
    public HealthTests(WebApplicationFactory<Program> f) => _factory = f;

    [Fact]
    public async Task Health_returns_ok()
    {
        var resp = await _factory.CreateClient().GetAsync("/health");
        Assert.Equal(HttpStatusCode.OK, resp.StatusCode);
        Assert.Contains("ok", await resp.Content.ReadAsStringAsync());
    }
}
