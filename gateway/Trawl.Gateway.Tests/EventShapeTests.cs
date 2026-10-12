using System.Text.Json;
using Trawl.Gateway;

public class EventShapeTests
{
    [Fact]
    public void QueryAnswered_serializes_to_camelCase_wire_shape()
    {
        var evt = new QueryAnsweredEvent(
            "what changed?", 5, 740, "echo", new long[] { 1, 2 }, true, "2026-10-12T00:00:00Z");
        using var doc = JsonDocument.Parse(EventJson.Serialize(evt));
        var root = doc.RootElement;
        Assert.Equal("what changed?", root.GetProperty("question").GetString());
        Assert.Equal(5, root.GetProperty("k").GetInt32());
        Assert.Equal(740, root.GetProperty("latencyMs").GetInt64());
        Assert.Equal("echo", root.GetProperty("provider").GetString());
        Assert.Equal(2, root.GetProperty("retrievedDocIds").GetArrayLength());
        Assert.True(root.GetProperty("cited").GetBoolean());
        Assert.Equal("2026-10-12T00:00:00Z", root.GetProperty("ts").GetString());
    }
}
