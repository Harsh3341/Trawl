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
    private readonly IEventPublisher _events;
    private readonly ILogger<AskController> _log;

    public AskController(IEmbeddingClient emb, IChunkRepository repo, ILlmProvider llm,
                         IEventPublisher events, ILogger<AskController> log)
    {
        _emb = emb; _repo = repo; _llm = llm; _events = events; _log = log;
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
        sw.Stop();

        try
        {
            _events.PublishQueryAnswered(new QueryAnsweredEvent(
                req.Question, k, sw.ElapsedMilliseconds, _llm.Name,
                hits.Select(h => h.DocumentId).Distinct().ToList(),
                citations.Count > 0, DateTimeOffset.UtcNow.ToString("O")));
        }
        catch (Exception ex) { _log.LogWarning(ex, "query.answered publish failed"); }

        return Ok(new AskResponse(answer, citations, sw.ElapsedMilliseconds));
    }
}
