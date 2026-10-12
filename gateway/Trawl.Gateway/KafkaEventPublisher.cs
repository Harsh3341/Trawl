using Confluent.Kafka;

namespace Trawl.Gateway;

public sealed class KafkaEventPublisher : IEventPublisher, IDisposable
{
    private readonly IProducer<string, string> _producer;
    private readonly ILogger<KafkaEventPublisher> _log;

    public KafkaEventPublisher(string bootstrap, ILogger<KafkaEventPublisher> log)
    {
        _log = log;
        _producer = new ProducerBuilder<string, string>(
            new ProducerConfig { BootstrapServers = bootstrap }).Build();
    }

    public void PublishQueryAnswered(QueryAnsweredEvent evt)
    {
        try
        {
            _producer.Produce("query.answered",
                new Message<string, string> { Value = EventJson.Serialize(evt) });
        }
        catch (Exception ex) { _log.LogWarning(ex, "query.answered publish failed"); }
    }

    public void Dispose() => _producer.Flush(TimeSpan.FromSeconds(5));
}
