using System.Text.Json;
using Confluent.Kafka;
using Confluent.Kafka.Admin;
using Microsoft.Extensions.Logging.Abstractions;
using Trawl.Gateway;

public class KafkaRoundTripTests
{
    private static string Bootstrap =>
        Environment.GetEnvironmentVariable("KAFKA_BOOTSTRAP_SERVERS") ?? "localhost:29092";

    private static bool BrokerReachable()
    {
        try
        {
            using var admin = new AdminClientBuilder(
                new AdminClientConfig { BootstrapServers = Bootstrap }).Build();
            admin.GetMetadata(TimeSpan.FromSeconds(3));
            return true;
        }
        catch { return false; }
    }

    [Fact]
    public void Publishes_query_answered_that_a_consumer_reads_back()
    {
        if (!BrokerReachable()) return; // skipped: no broker on this host

        var evt = new QueryAnsweredEvent(
            "round trip?", 5, 10, "echo", new long[] { 42 }, true,
            DateTimeOffset.UtcNow.ToString("O"));

        using var consumer = new ConsumerBuilder<string, string>(new ConsumerConfig
        {
            BootstrapServers = Bootstrap, GroupId = $"test-{Guid.NewGuid()}",
            AutoOffsetReset = AutoOffsetReset.Latest, EnableAutoCommit = false,
        }).Build();
        consumer.Subscribe("query.answered");
        consumer.Consume(TimeSpan.FromSeconds(2)); // join group / assign partitions

        using (var pub = new KafkaEventPublisher(Bootstrap, NullLogger<KafkaEventPublisher>.Instance))
            pub.PublishQueryAnswered(evt);

        ConsumeResult<string, string>? got = null;
        var deadline = DateTime.UtcNow.AddSeconds(10);
        while (DateTime.UtcNow < deadline && got is null)
            got = consumer.Consume(TimeSpan.FromSeconds(1));

        Assert.NotNull(got);
        using var doc = JsonDocument.Parse(got!.Message.Value);
        Assert.Equal("round trip?", doc.RootElement.GetProperty("question").GetString());
        Assert.Equal("echo", doc.RootElement.GetProperty("provider").GetString());
    }
}
