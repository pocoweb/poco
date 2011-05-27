Installation Configurations:
    Configure Flume
    start each Flume node on every machine which runs the api server.
    configure each flume node like this:
        Source: syslogTcp(5140)
        Sink: collectorSink("hdfs://FIXME", "<node_name>")
