using System.IdentityModel.Tokens.Jwt;
using System.Security.Claims;
using System.Text;
using Microsoft.IdentityModel.Tokens;
namespace Trawl.Gateway;

public static class JwtConfig
{
    public const string Issuer = "trawl";
    public const string Audience = "trawl";

    public static SymmetricSecurityKey Key(string secret) => new(Encoding.UTF8.GetBytes(secret));

    public static string Issue(string secret, string subject = "dev")
    {
        var creds = new SigningCredentials(Key(secret), SecurityAlgorithms.HmacSha256);
        var token = new JwtSecurityToken(Issuer, Audience,
            claims: new[] { new Claim(ClaimTypes.NameIdentifier, subject) },
            expires: DateTime.UtcNow.AddHours(1), signingCredentials: creds);
        return new JwtSecurityTokenHandler().WriteToken(token);
    }
}
