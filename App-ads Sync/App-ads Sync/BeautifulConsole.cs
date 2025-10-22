namespace AppAdsSync
{
    public static class BeautifulConsole
    {
        public static void WriteLineSuccess(string message)
        {
            Console.ForegroundColor = ConsoleColor.Green;
            Console.Write("[SUCCESS] ");
            Console.ResetColor();
            Console.WriteLine(message);
        }

        public static void WriteLineFailure(string message) 
        {
            Console.ForegroundColor = ConsoleColor.Red;
            Console.Write("[FAILURE] ");
            Console.ResetColor();
            Console.WriteLine(message);
        }

        public static string ClampedString(string message, int maxLenth)
        {
            if (message.Length > maxLenth)
            {
                return message.Substring(0, maxLenth) + "...";
            }
            return message;
        }
    }
}
