using Microsoft.Extensions.Logging;
using Npgsql;

internal static class PostgresDatabaseBootstrap
{
    internal static void EnsureDatabaseExists(string connectionString, ILogger logger)
    {
        if (string.IsNullOrWhiteSpace(connectionString))
        {
            throw new InvalidOperationException("Connection string 'Connection' is not configured.");
        }

        var targetBuilder = new NpgsqlConnectionStringBuilder(connectionString);
        var databaseName = targetBuilder.Database?.Trim();
        if (string.IsNullOrWhiteSpace(databaseName))
        {
            throw new InvalidOperationException("Target PostgreSQL database name is missing from the connection string.");
        }

        var adminBuilder = new NpgsqlConnectionStringBuilder(connectionString)
        {
            Database = "postgres",
            Pooling = false,
        };

        using var connection = new NpgsqlConnection(adminBuilder.ConnectionString);
        connection.Open();

        using var existsCommand = new NpgsqlCommand(
            "SELECT 1 FROM pg_database WHERE datname = @databaseName;",
            connection);
        existsCommand.Parameters.AddWithValue("databaseName", databaseName);

        if (existsCommand.ExecuteScalar() is not null)
        {
            logger.LogInformation(
                "Verified PostgreSQL database {DatabaseName} exists before applying migrations.",
                databaseName);
            return;
        }

        logger.LogWarning(
            "PostgreSQL database {DatabaseName} does not exist. Creating it before applying migrations.",
            databaseName);

        var quotedDatabaseName = QuoteIdentifier(databaseName);
        using var createCommand = new NpgsqlCommand($"CREATE DATABASE {quotedDatabaseName};", connection);
        createCommand.ExecuteNonQuery();

        logger.LogInformation(
            "Created PostgreSQL database {DatabaseName}.",
            databaseName);
    }

    private static string QuoteIdentifier(string identifier) =>
        "\"" + identifier.Replace("\"", "\"\"") + "\"";
}
