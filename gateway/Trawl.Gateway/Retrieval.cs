using Npgsql;
using Pgvector;
namespace Trawl.Gateway;

public interface IChunkRepository
{
    Task<IReadOnlyList<RetrievedChunk>> SearchAsync(float[] embedding, int k, CancellationToken ct = default);
}

public class PgChunkRepository : IChunkRepository
{
    private readonly NpgsqlDataSource _db;
    public PgChunkRepository(NpgsqlDataSource db) => _db = db;

    public async Task<IReadOnlyList<RetrievedChunk>> SearchAsync(
        float[] embedding, int k, CancellationToken ct = default)
    {
        await using var cmd = _db.CreateCommand(@"
            SELECT d.id, d.url, d.title, d.version, c.text, 1 - (c.embedding <=> $1) AS score
            FROM chunks c JOIN documents d ON d.id = c.document_id
            ORDER BY c.embedding <=> $1
            LIMIT $2");
        cmd.Parameters.Add(new NpgsqlParameter { Value = new Vector(embedding) });
        cmd.Parameters.Add(new NpgsqlParameter { Value = k });

        var results = new List<RetrievedChunk>();
        await using var reader = await cmd.ExecuteReaderAsync(ct);
        while (await reader.ReadAsync(ct))
            results.Add(new RetrievedChunk(
                reader.GetInt64(0), reader.GetString(1), reader.GetString(2),
                reader.IsDBNull(3) ? null : reader.GetString(3),
                reader.GetString(4), reader.GetDouble(5)));
        return results;
    }
}
