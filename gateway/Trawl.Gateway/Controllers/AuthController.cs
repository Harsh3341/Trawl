using Microsoft.AspNetCore.Mvc;

namespace Trawl.Gateway.Controllers;

[ApiController]
public class AuthController : ControllerBase
{
    private readonly IConfiguration _cfg;
    public AuthController(IConfiguration cfg) => _cfg = cfg;

    // Dev-only helper: mints a short-lived JWT so the slice is runnable offline.
    [HttpPost("/token")]
    public IActionResult Token()
    {
        var secret = _cfg["JWT_SECRET"] ?? throw new InvalidOperationException("JWT_SECRET not set");
        return Ok(new { token = JwtConfig.Issue(secret) });
    }
}
