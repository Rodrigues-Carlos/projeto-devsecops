using System.Globalization;
using System.Text.Json;
using System.Text.Json.Serialization;
using Microsoft.Extensions.FileProviders;

var builder = WebApplication.CreateBuilder(args);

builder.Services.ConfigureHttpJsonOptions(options =>
{
    options.SerializerOptions.PropertyNamingPolicy = JsonNamingPolicy.CamelCase;
    options.SerializerOptions.Converters.Add(new JsonStringEnumConverter());
});

builder.Services.AddCors(options =>
{
    options.AddDefaultPolicy(policy =>
        policy.AllowAnyOrigin()
            .AllowAnyHeader()
            .AllowAnyMethod());
});

var dataFile = builder.Configuration["Scheduling:DataFile"]
    ?? Path.Combine(builder.Environment.ContentRootPath, "data", "agendamentos.json");
builder.Services.AddSingleton(new AgendamentoStore(dataFile));

var app = builder.Build();

app.UseCors();

var webDirectory = Path.GetFullPath(
    Path.Combine(builder.Environment.ContentRootPath, "..", "..", "apps", "web"));

if (Directory.Exists(webDirectory))
{
    var webFiles = new PhysicalFileProvider(webDirectory);
    app.UseDefaultFiles(new DefaultFilesOptions
    {
        FileProvider = webFiles
    });
    app.UseStaticFiles(new StaticFileOptions
    {
        FileProvider = webFiles
    });
}

app.MapGet("/health", () => Results.Ok(new { status = "ok" }));

app.MapGet("/agendamentos", async (AgendamentoStore store, CancellationToken cancellationToken) =>
{
    var agendamentos = await store.ListarAsync(cancellationToken);
    return Results.Ok(agendamentos);
});

app.MapPost("/agendamentos", async (
    CriarAgendamentoRequest request,
    AgendamentoStore store,
    CancellationToken cancellationToken) =>
{
    var erros = Validar(request);
    if (erros.Count > 0)
    {
        return Results.ValidationProblem(erros);
    }

    var agendamento = new Agendamento(
        Guid.NewGuid(),
        request.Nome.Trim(),
        request.Servico.Trim(),
        request.Barbeiro.Trim(),
        request.Data,
        request.Horario);

    var criado = await store.AdicionarAsync(agendamento, cancellationToken);
    if (!criado)
    {
        return Results.Conflict(new
        {
            mensagem = "Ja existe um agendamento para esse barbeiro, data e horario."
        });
    }

    return Results.Json(agendamento, statusCode: StatusCodes.Status201Created);
});

app.Run();

static Dictionary<string, string[]> Validar(CriarAgendamentoRequest request)
{
    var erros = new Dictionary<string, string[]>();
    var barbeiroValido = !string.IsNullOrWhiteSpace(request.Barbeiro)
        && RegrasAgendamento.HorariosPorBarbeiro.ContainsKey(request.Barbeiro.Trim());

    if (string.IsNullOrWhiteSpace(request.Nome))
    {
        erros["nome"] = ["O nome e obrigatorio."];
    }
    else if (request.Nome.Trim().Length > 100)
    {
        erros["nome"] = ["O nome deve ter no maximo 100 caracteres."];
    }

    if (string.IsNullOrWhiteSpace(request.Servico))
    {
        erros["servico"] = ["O servico e obrigatorio."];
    }
    else if (!RegrasAgendamento.Servicos.Contains(request.Servico.Trim()))
    {
        erros["servico"] = ["O servico informado nao e valido."];
    }
    else if (request.Servico.Trim().Length > 100)
    {
        erros["servico"] = ["O servico deve ter no maximo 100 caracteres."];
    }

    if (string.IsNullOrWhiteSpace(request.Barbeiro))
    {
        erros["barbeiro"] = ["O barbeiro e obrigatorio."];
    }
    else if (!barbeiroValido)
    {
        erros["barbeiro"] = ["O barbeiro informado nao e valido."];
    }
    else if (request.Barbeiro.Trim().Length > 100)
    {
        erros["barbeiro"] = ["O barbeiro deve ter no maximo 100 caracteres."];
    }

    if (request.Data < DateOnly.FromDateTime(DateTime.Today))
    {
        erros["data"] = ["A data nao pode estar no passado."];
    }

    if (!TimeOnly.TryParseExact(
        request.Horario,
        "HH:mm",
        CultureInfo.InvariantCulture,
        DateTimeStyles.None,
        out _))
    {
        erros["horario"] = ["O horario deve usar o formato HH:mm."];
    }
    else if (barbeiroValido
        && !RegrasAgendamento.HorariosPorBarbeiro[request.Barbeiro.Trim()]
            .Contains(request.Horario))
    {
        erros["horario"] = ["O barbeiro nao atende no horario informado."];
    }

    return erros;
}

public static class RegrasAgendamento
{
    public static readonly HashSet<string> Servicos =
    [
        "Corte de cabelo",
        "Barba",
        "Corte + barba"
    ];

    public static readonly Dictionary<string, HashSet<string>> HorariosPorBarbeiro = new()
    {
        ["Nathan"] = ["08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00"],
        ["Carlos"] = ["11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:00"],
        ["Leonardo"] = ["09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00"]
    };
}

public sealed record CriarAgendamentoRequest(
    string Nome,
    string Servico,
    string Barbeiro,
    DateOnly Data,
    string Horario);

public sealed record Agendamento(
    Guid Id,
    string Nome,
    string Servico,
    string Barbeiro,
    DateOnly Data,
    string Horario);

public sealed class AgendamentoStore
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
        WriteIndented = true
    };

    private readonly string _dataFile;
    private readonly SemaphoreSlim _lock = new(1, 1);

    public AgendamentoStore(string dataFile)
    {
        _dataFile = dataFile;
    }

    public async Task<IReadOnlyList<Agendamento>> ListarAsync(CancellationToken cancellationToken)
    {
        await _lock.WaitAsync(cancellationToken);
        try
        {
            var agendamentos = await CarregarAsync(cancellationToken);
            return agendamentos
                .OrderBy(item => item.Data)
                .ThenBy(item => item.Horario)
                .ToArray();
        }
        finally
        {
            _lock.Release();
        }
    }

    public async Task<bool> AdicionarAsync(
        Agendamento agendamento,
        CancellationToken cancellationToken)
    {
        await _lock.WaitAsync(cancellationToken);
        try
        {
            var agendamentos = await CarregarAsync(cancellationToken);
            var horarioOcupado = agendamentos.Any(item =>
                string.Equals(item.Barbeiro, agendamento.Barbeiro, StringComparison.OrdinalIgnoreCase)
                && item.Data == agendamento.Data
                && item.Horario == agendamento.Horario);

            if (horarioOcupado)
            {
                return false;
            }

            agendamentos.Add(agendamento);
            await SalvarAsync(agendamentos, cancellationToken);
            return true;
        }
        finally
        {
            _lock.Release();
        }
    }

    private async Task<List<Agendamento>> CarregarAsync(CancellationToken cancellationToken)
    {
        if (!File.Exists(_dataFile))
        {
            return [];
        }

        await using var stream = File.OpenRead(_dataFile);
        return await JsonSerializer.DeserializeAsync<List<Agendamento>>(
            stream,
            JsonOptions,
            cancellationToken) ?? [];
    }

    private async Task SalvarAsync(
        List<Agendamento> agendamentos,
        CancellationToken cancellationToken)
    {
        var directory = Path.GetDirectoryName(_dataFile);
        if (!string.IsNullOrEmpty(directory))
        {
            Directory.CreateDirectory(directory);
        }

        var temporaryFile = $"{_dataFile}.tmp";
        await using (var stream = File.Create(temporaryFile))
        {
            await JsonSerializer.SerializeAsync(
                stream,
                agendamentos,
                JsonOptions,
                cancellationToken);
        }

        File.Move(temporaryFile, _dataFile, true);
    }
}
