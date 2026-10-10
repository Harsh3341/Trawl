using System.Text;
namespace Trawl.Gateway;

public interface ILlmProvider
{
    string Complete(string question, IReadOnlyList<RetrievedChunk> contexts);
}

// Deterministic, offline default: summarizes retrieved context without an API call.
public class EchoLlmProvider : ILlmProvider
{
    public string Complete(string question, IReadOnlyList<RetrievedChunk> contexts)
    {
        if (contexts.Count == 0)
            return "I have no indexed documents that cover this question.";
        var sb = new StringBuilder();
        sb.AppendLine($"Based on {contexts.Count} indexed passage(s):");
        foreach (var c in contexts)
            sb.AppendLine($"- ({c.Version ?? c.Title}) {c.Text.Trim()}");
        return sb.ToString().TrimEnd();
    }
}
