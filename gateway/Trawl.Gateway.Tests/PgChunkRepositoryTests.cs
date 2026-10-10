using Npgsql;
using Pgvector;
using Pgvector.Npgsql;
using Trawl.Gateway;

public class PgChunkRepositoryTests : IAsyncLifetime
{
    private const string Conn =
        "Host=localhost;Port=5432;Username=trawl;Password=trawl;Database=trawl_test";
    private NpgsqlDataSource _ds = null!;

    private static float[] OneHot(int i) { var v = new float[768]; v[i] = 1f; return v; }

    public async Task InitializeAsync()
    {
        var b = new NpgsqlDataSourceBuilder(Conn); b.UseVector(); _ds = b.Build();
        await using (var cmd = _ds.CreateCommand(
            "TRUNCATE sources, documents, chunks RESTART IDENTITY CASCADE"))
            await cmd.ExecuteNonQueryAsync();
        await using (var seed = _ds.CreateCommand(@"
            INSERT INTO sources(id,name,kind,seed_url) VALUES (1,'r','github_release','u');
            INSERT INTO documents(id,source_id,url,title,version,content_text,content_hash,status)
              VALUES (1,1,'https://x/1','v2','v2','t','h','embedded')"))
            await seed.ExecuteNonQueryAsync();
        await InsertChunk(0, "dark mode", OneHot(3));
        await InsertChunk(1, "login bug", OneHot(10));
    }

    private async Task InsertChunk(int ordinal, string text, float[] embedding)
    {
        await using var cmd = _ds.CreateCommand(
            @"INSERT INTO chunks(document_id,ordinal,text,embedding,token_count)
              VALUES (1,$1,$2,$3,2)");
        cmd.Parameters.Add(new NpgsqlParameter { Value = ordinal });
        cmd.Parameters.Add(new NpgsqlParameter { Value = text });
        cmd.Parameters.Add(new NpgsqlParameter { Value = new Vector(embedding) });
        await cmd.ExecuteNonQueryAsync();
    }

    public Task DisposeAsync() { _ds.Dispose(); return Task.CompletedTask; }

    [Fact]
    public async Task Search_orders_by_cosine_similarity()
    {
        var hits = await new PgChunkRepository(_ds).SearchAsync(OneHot(3), 2);
        Assert.Equal(2, hits.Count);
        Assert.Equal("dark mode", hits[0].Text);     // nearest to query vector
        Assert.True(hits[0].Score > hits[1].Score);
        Assert.Equal(1, hits[0].DocumentId);
    }
}
