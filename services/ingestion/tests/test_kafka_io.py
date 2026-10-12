def test_module_imports_without_confluent_kafka_installed():
    # Adapters import confluent-kafka lazily, so this must succeed even in the
    # dev venv where the 'kafka' extra is not installed.
    import app.kafka_io as k
    assert hasattr(k, "KafkaProducer")
    assert hasattr(k, "KafkaConsumer")
    assert hasattr(k, "create_topics")
    assert k.bootstrap_servers()  # falls back to localhost:29092
