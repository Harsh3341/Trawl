using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.IdentityModel.Tokens;
using Npgsql;
using Pgvector.Npgsql;
using Trawl.Gateway;

var builder = WebApplication.CreateBuilder(args);
var cfg = builder.Configuration;
var secret = cfg["JWT_SECRET"] ?? throw new InvalidOperationException("JWT_SECRET not set");
var embUrl = cfg["EMBEDDING_URL"] ?? "http://localhost:8000";
var dbConn = cfg["GATEWAY_DB"] ?? "Host=localhost;Username=trawl;Password=trawl;Database=trawl";

var dsb = new NpgsqlDataSourceBuilder(dbConn); dsb.UseVector();
builder.Services.AddSingleton(dsb.Build());
builder.Services.AddSingleton<IChunkRepository, PgChunkRepository>();
builder.Services.AddSingleton<ILlmProvider, EchoLlmProvider>();
builder.Services.AddHttpClient<IEmbeddingClient, HttpEmbeddingClient>(
    c => c.BaseAddress = new Uri(embUrl));

builder.Services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
    .AddJwtBearer(o => o.TokenValidationParameters = new TokenValidationParameters
    {
        ValidIssuer = JwtConfig.Issuer, ValidAudience = JwtConfig.Audience,
        IssuerSigningKey = JwtConfig.Key(secret),
        ValidateIssuer = true, ValidateAudience = true, ValidateIssuerSigningKey = true,
    });
builder.Services.AddAuthorization();
builder.Services.AddControllers();

var app = builder.Build();
app.UseAuthentication();
app.UseAuthorization();
app.MapControllers();

app.Run();

public partial class Program { }   // exposes Program to WebApplicationFactory
