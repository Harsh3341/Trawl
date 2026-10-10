using System.Diagnostics;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace Trawl.Gateway.Controllers;

[ApiController]
[Authorize]
public class AskController : ControllerBase
{
    private readonly IEmbeddingClient _emb;
    private readonly IChunkRepository _repo;
    private readonly ILlmProvider _llm;

    public AskController(IEmbeddingClient emb, IChunkRepository repo, ILlmProvider llm)
    {
        _emb = emb;
        _repo = repo;
        _llm = llm;
    }

    [HttpPost("/ask")]
    public async Task<IActionResult> Ask([FromBody] AskRequest req, CancellationToken ct)
    {
        if (string.IsNullOrWhiteSpace(req.Question) || req.Question.Length > 2000)
            return BadRequest(new { error = "question must be 1..2000 chars" });

        var sw = Stopwatch.StartNew();
        var k = Math.Clamp(req.K, 1, 20);
        var hits = await _repo.SearchAsync(await _emb.EmbedAsync(req.Question, ct), k, ct);
        var answer = _llm.Complete(req.Question, hits);
        var citations = hits.GroupBy(h => h.DocumentId).Select(g => g.First())
            .Select(h => new Citation(h.DocumentId, h.Url, h.Title, h.Version)).ToList();
        return Ok(new AskResponse(answer, citations, sw.ElapsedMilliseconds));
    }
}
