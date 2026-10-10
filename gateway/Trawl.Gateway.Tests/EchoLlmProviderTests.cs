using Trawl.Gateway;

public class EchoLlmProviderTests
{
    [Fact]
    public void Compose_grounds_answer_in_context()
    {
        var ctx = new List<RetrievedChunk>
        {
            new(1, "https://x/1", "v2.0.0", "v2.0.0", "Added dark mode.", 0.9),
            new(1, "https://x/1", "v2.0.0", "v2.0.0", "Fixed login bug.", 0.8),
        };
        var answer = new EchoLlmProvider().Complete("what changed?", ctx);
        Assert.Contains("dark mode", answer);
        Assert.Contains("v2.0.0", answer);
    }

    [Fact]
    public void Compose_handles_no_context()
    {
        var answer = new EchoLlmProvider().Complete("anything", new List<RetrievedChunk>());
        Assert.Contains("no indexed", answer, StringComparison.OrdinalIgnoreCase);
    }
}
