using Server;

WebApplicationBuilder builder = WebApplication.CreateBuilder(args);

Startup startup = new(builder.Configuration);
startup.ConfigureServices(builder.Services);

WebApplication app = builder.Build();

startup.Configure(app, app.Environment);

app.Run();