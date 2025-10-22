using System.Text.Json;

namespace AppAdsSync
{
    public class Configuration
    {
        public string? SourceURL { get; set; }
        public string? TargetFilePath { get; set; }

        private const string FileName = "config.json";

        public Configuration() { } 

        public static Configuration LoadOrCreate()
        {
            if (File.Exists(FileName))
            {
                try
                {
                    string json = File.ReadAllText(FileName);
                    Configuration? loadedConfig = JsonSerializer.Deserialize<Configuration>(json);

                    if (loadedConfig == null)
                    {
                        throw new Exception($"Unable to read {FileName} configuration file");
                    }

                    BeautifulConsole.WriteLineSuccess($"Configuration file {FileName} was loaded");
                    return loadedConfig;
                }
                catch (Exception ex)
                {
                    BeautifulConsole.WriteLineFailure($"Unable to read {FileName} configuration file: {ex.Message}\n");
                    return RequestAndSaveConfig();
                }
            }
            else
            {
                return RequestAndSaveConfig();
            }
        }

        public static Configuration RequestAndSaveConfig()
        {
            Configuration configuration = new Configuration();

            Console.ForegroundColor = ConsoleColor.Yellow;
            Console.Write("Enter source App-Ads.txt URL: ");
            Console.ResetColor();
            configuration.SourceURL = Console.ReadLine();

            Console.ForegroundColor = ConsoleColor.Yellow;
            Console.Write("Enter target file path to save App-Ads.txt: ");
            Console.ResetColor();
            configuration.TargetFilePath = Console.ReadLine()!.Replace("\"", "");

            JsonSerializerOptions options = new JsonSerializerOptions { WriteIndented = true };
            string json = JsonSerializer.Serialize(configuration, options);
            File.WriteAllText(FileName, json);

            BeautifulConsole.WriteLineSuccess("Configuration file was saved");
            return configuration;
        }
    }
}
