using Microsoft.AspNetCore.Mvc;

namespace Trawl.Gateway.Controllers;

[ApiController]
public class HealthController : ControllerBase
{
    [HttpGet("/health")]
    public IActionResult Get() => Ok(new { status = "ok" });
}
