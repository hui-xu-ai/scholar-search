using System;
using System.Diagnostics;
using System.IO;

// Native messaging hosts must be real executables; Edge will not launch a .cmd.
// This launcher starts the project's Python entry point and inherits stdio.
class ScholarHostLauncher
{
    static void Log(string message)
    {
        try
        {
            string path = Path.Combine(Path.GetTempPath(), "scholar-launcher.log");
            File.AppendAllText(path, DateTime.Now.ToString("s") + " " + message + Environment.NewLine);
        }
        catch
        {
            // Diagnostics must never break the host.
        }
    }

    static int Main(string[] args)
    {
        string baseDir = AppDomain.CurrentDomain.BaseDirectory;
        string pythonFile = Path.Combine(baseDir, "python-path.txt");
        string python = File.Exists(pythonFile)
            ? File.ReadAllText(pythonFile).Trim()
            : Path.GetFullPath(Path.Combine(baseDir, "..", ".venv", "Scripts", "python.exe"));
        string script = Path.Combine(baseDir, "main.py");

        Log("start base=" + baseDir + " python=" + python + " args=" + string.Join("|", args));

        if (!File.Exists(python) || !File.Exists(script))
        {
            Log("missing python or script");
            Console.Error.WriteLine("scholar-search host: python or main.py not found");
            return 2;
        }

        var info = new ProcessStartInfo
        {
            FileName = python,
            Arguments = "-u \"" + script + "\"",
            UseShellExecute = false,
            CreateNoWindow = true,
            WorkingDirectory = baseDir,
            RedirectStandardError = true
        };

        try
        {
            using (var process = Process.Start(info))
            {
                Log("python started pid=" + process.Id);
                string stderr = process.StandardError.ReadToEnd();
                process.WaitForExit();
                if (stderr.Length > 0) Log("stderr: " + stderr.Trim());
                Log("python exited code=" + process.ExitCode);
                return process.ExitCode;
            }
        }
        catch (Exception error)
        {
            Log("start failed: " + error.Message);
            return 3;
        }
    }
}
