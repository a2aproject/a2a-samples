using System.Text.Json.Serialization;
using A2A;
using A2A.AspNetCore;
using Github;
using Microsoft.SemanticKernel;
using ModelContextProtocol.Client;
using Server.Services;
using McpClientFactory = Github.McpClientFactory;

namespace Server;

public class Startup(IConfiguration configuration)
{
    private IConfiguration Configuration { get; } = configuration;

    public void ConfigureServices(IServiceCollection services)
    {
        services.AddControllers()
            .AddJsonOptions(options =>
            {
                options.JsonSerializerOptions.DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull;
                options.JsonSerializerOptions.Converters.Add(new JsonStringEnumConverter());
            });

        services.AddEndpointsApiExplorer();
        services.AddSwaggerGen();

        services.AddLogging(builder =>
        {
            builder.AddConsole();
            builder.AddDebug();
            builder.SetMinimumLevel(LogLevel.Information);
        });

        services.AddSingleton<IMcpClientFactory, McpClientFactory>();
        services.AddSingleton<McpClientService>();
        services.AddSingleton<IMcpClient>(_ => services.BuildServiceProvider().GetRequiredService<McpClientService>().CreateClient().Result!);
        services.AddSingleton(sp =>
        {
            KernelBuilder kernelBuilder = new(Configuration);
            ToolService toolService = sp.GetRequiredService<ToolService>();
            IList<McpClientTool> tools = toolService.GetGithubTools().GetAwaiter().GetResult();
            return kernelBuilder.BuildKernel(tools);
        });

        services.AddSingleton(sp =>
        {
            Kernel kernel = sp.GetRequiredService<Kernel>();
            AgentFactory agentFactory = new(kernel);
            return agentFactory.CreateGithubAgent();
        });

        services.AddSingleton<AgentFactory>();
        services.AddScoped<AgentService>();
        services.AddSingleton<ToolService>();

        services.AddScoped<GitHubA2AAgent>();
        services.AddSingleton<ITaskManager, TaskManager>();

        services.AddCors(options =>
        {
            options.AddPolicy("AllowAll", builder =>
            {
                builder.AllowAnyOrigin()
                       .AllowAnyMethod()
                       .AllowAnyHeader();
            });
        });

        services.AddHealthChecks();
    }

    public void Configure(WebApplication app, IWebHostEnvironment env)
    {
        if (env.IsDevelopment())
        {
            app.UseSwagger();
            app.UseSwaggerUI();
            app.UseDeveloperExceptionPage();
        }
        else
        {
            app.UseExceptionHandler("/Error");
            app.UseHsts();
        }

        app.UseHttpsRedirection();
        app.UseRouting();
        app.UseCors("AllowAll");

        app.MapControllers();

        app.MapHealthChecks("/health");

        using (IServiceScope scope = app.Services.CreateScope())
        {
            IServiceProvider serviceProvider = scope.ServiceProvider;
            GitHubA2AAgent githubAgent = serviceProvider.GetRequiredService<GitHubA2AAgent>();
            ITaskManager taskManager = serviceProvider.GetRequiredService<ITaskManager>();

            Task.Run(async () =>
            {
                try
                {
                    await githubAgent.InitializeAsync();
                    githubAgent.Attach(taskManager);

                    ILogger<Startup> logger = serviceProvider.GetRequiredService<ILogger<Startup>>();
                    logger.LogInformation("GitHub A2A Agent initialized and attached successfully");
                }
                catch (Exception ex)
                {
                    ILogger<Startup> logger = serviceProvider.GetRequiredService<ILogger<Startup>>();
                    logger.LogError(ex, "Failed to initialize GitHub A2A Agent");
                    throw;
                }
            });

            app.MapA2A(taskManager, "/github-agent");
        }

        app.MapGet("/", () => new
        {
            Service = "GitHub A2A Agent Server",
            Version = "1.0.0",
            Endpoints = new
            {
                Agent = "/github-agent",
                Health = "/health",
                Swagger = "/swagger"
            }
        });
    }
}