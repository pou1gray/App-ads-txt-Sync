using AppAdsSync;

Configuration configuration = Configuration.LoadOrCreate();

using (HttpClient client = new HttpClient())
{
    try
    {
        string content = await client.GetStringAsync(configuration.SourceURL);
        BeautifulConsole.WriteLineSuccess($"Source app-ads.txt was loaded from {BeautifulConsole.ClampedString(configuration.SourceURL!, 60)}");

        Directory.CreateDirectory(Path.GetDirectoryName(configuration.TargetFilePath)!);
        await File.WriteAllTextAsync(configuration.TargetFilePath!, content);
        BeautifulConsole.WriteLineSuccess($"File {configuration.TargetFilePath} successfully updated!");

        Console.ForegroundColor = ConsoleColor.Green;
        Console.WriteLine(" --- All done! Push the changes to finish syncing! --- ");
        Console.ResetColor();
    }
    catch (HttpRequestException e)
    {
        BeautifulConsole.WriteLineSuccess($" Source file load error: {e.Message}");
    }
}

Console.ReadKey();
