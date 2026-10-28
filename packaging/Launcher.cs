using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Text;
using System.Threading;
using System.Windows.Forms;
using System.Web.Script.Serialization;

class MissionWindow : Form {
    readonly string root = AppDomain.CurrentDomain.BaseDirectory;
    readonly NumericUpDown first = new NumericUpDown(), last = new NumericUpDown();
    readonly Button run = new Button(), stop = new Button(), check = new Button();
    readonly Label status = new Label();
    readonly TextBox log = new TextBox();
    readonly System.Windows.Forms.Timer timer = new System.Windows.Forms.Timer();
    Process worker;
    bool runningTask, closeWhenStopped;
    string Output { get { return Path.Combine(root, "app", "output"); } }

    public MissionWindow() {
        Text = "蔚蓝档案 · 活动任务助手";
        Icon = System.Drawing.Icon.ExtractAssociatedIcon(Application.ExecutablePath);
        ClientSize = new Size(780, 535);
        MinimumSize = new Size(650, 500);
        StartPosition = FormStartPosition.CenterScreen;
        Font = new Font("Microsoft YaHei UI", 10);
        BackColor = Color.FromArgb(245, 248, 252);
        var title = new Label { Text = "活动任务 01—12", Font = new Font(Font.FontFamily, 19, FontStyle.Bold), AutoSize = true, Location = new Point(24, 20) };
        var hint = new Label { Text = "日服 PC · 简体中文画面识别 · 已三星自动跳过", AutoSize = true, ForeColor = Color.FromArgb(75, 90, 110), Location = new Point(27, 65) };
        var prepare = new Label { Text = "先打开游戏的活动「任务」列表，并选好出战队伍，再点击开始。", AutoSize = true, Location = new Point(27, 99) };
        var range = new Label { Text = "关卡范围", AutoSize = true, Location = new Point(27, 144) };
        first.SetBounds(110, 139, 70, 29); last.SetBounds(215, 139, 70, 29);
        first.Minimum = last.Minimum = 1; first.Maximum = last.Maximum = 12; first.Value = 1; last.Value = 12;
        var to = new Label { Text = "至", AutoSize = true, Location = new Point(187, 144) };
        run.Text = "开始任务"; run.SetBounds(315, 135, 130, 38);
        run.BackColor = Color.FromArgb(31, 111, 210); run.ForeColor = Color.White; run.FlatStyle = FlatStyle.Flat;
        stop.Text = "停止"; stop.SetBounds(456, 135, 100, 38); stop.Enabled = false;
        check.Text = "检查环境"; check.SetBounds(568, 135, 110, 38);
        status.Text = "就绪 · 每关最多尝试一次，不购买体力"; status.SetBounds(27, 188, 720, 28);
        status.Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right;
        log.Multiline = true; log.ReadOnly = true; log.ScrollBars = ScrollBars.Vertical;
        log.Font = new Font("Consolas", 9); log.SetBounds(27, 228, 726, 242);
        log.Anchor = AnchorStyles.Top | AnchorStyles.Bottom | AnchorStyles.Left | AnchorStyles.Right;
        var folder = new Button { Text = "查看报告和日志", Location = new Point(27, 485), Size = new Size(160, 30), Anchor = AnchorStyles.Left | AnchorStyles.Bottom };
        var footer = new Label { Text = "界面更新后可能需要更新中文模板。停止后会保留已完成的关卡。", AutoSize = true, Location = new Point(210, 491), Anchor = AnchorStyles.Left | AnchorStyles.Bottom, ForeColor = Color.DimGray };
        Controls.AddRange(new Control[] {title, hint, prepare, range, first, to, last, run, stop, check, status, log, folder, footer});
        run.Click += delegate { if (first.Value > last.Value) { status.Text = "开始关卡不能大于结束关卡"; return; } StartWorker("--run --start " + first.Value + " --end " + last.Value, true); };
        check.Click += delegate { StartWorker("--verify-libraries", false); };
        stop.Click += delegate { StopTask(); };
        folder.Click += delegate { Directory.CreateDirectory(Output); Process.Start("explorer.exe", "\"" + Output + "\""); };
        timer.Interval = 1000; timer.Tick += delegate { RefreshProgress(); }; timer.Start();
        FormClosing += delegate(object sender, FormClosingEventArgs e) { if (worker != null) { closeWhenStopped = true; StopTask(); e.Cancel = true; } };
    }

    void Append(string text) {
        if (text == null || IsDisposed) return;
        if (InvokeRequired) { try { BeginInvoke(new Action<string>(Append), text); } catch (InvalidOperationException) {} return; }
        log.AppendText(text + Environment.NewLine);
    }
    void SetBusy(bool busy) { run.Enabled = check.Enabled = first.Enabled = last.Enabled = !busy; stop.Enabled = busy && runningTask; }
    void StartWorker(string arguments, bool task) {
        if (worker != null) return;
        try {
            Directory.CreateDirectory(Output);
            if (task && File.Exists(Path.Combine(Output, "STOP"))) File.Delete(Path.Combine(Output, "STOP"));
            runningTask = task; log.Clear(); status.Text = task ? "正在启动任务…" : "正在检查便携运行环境…";
            var info = Runner.Info(root, arguments);
            var process = new Process { StartInfo = info, EnableRaisingEvents = true };
            process.OutputDataReceived += delegate(object s, DataReceivedEventArgs e) { Append(e.Data); };
            process.ErrorDataReceived += delegate(object s, DataReceivedEventArgs e) { Append(e.Data); };
            process.Exited += delegate {
                int code = process.ExitCode;
                try { BeginInvoke(new Action(delegate {
                    worker = null; process.Dispose(); SetBusy(false);
                    status.Text = task ? (code == 0 ? "完成 · 所选关卡均已确认三星" : "已停止 · 详情见日志与报告") : (code == 0 ? "检查通过 · 可独立运行" : "环境检查未通过 · 详情见日志");
                    if (closeWhenStopped) Close();
                })); } catch (InvalidOperationException) {}
            };
            worker = process; SetBusy(true);
            process.Start(); process.BeginOutputReadLine(); process.BeginErrorReadLine();
        } catch (Exception e) { worker = null; SetBusy(false); status.Text = "启动失败"; Append(e.Message); }
    }
    void StopTask() {
        if (worker == null) return;
        if (!runningTask) { status.Text = "正在完成环境检查，请稍候…"; return; }
        Directory.CreateDirectory(Output); File.WriteAllText(Path.Combine(Output, "STOP"), "stop", Encoding.UTF8);
        status.Text = "正在停止 · 等待当前识别返回"; stop.Enabled = false;
    }
    void RefreshProgress() {
        if (worker == null || !runningTask || !stop.Enabled) return;
        try {
            string file = Path.Combine(Output, "result.json");
            if (!File.Exists(file)) return;
            var data = new JavaScriptSerializer().Deserialize<Dictionary<string, object>>(File.ReadAllText(file, Encoding.UTF8));
            var verified = data["verified"] as System.Collections.ArrayList;
            int count = verified == null ? 0 : verified.Count;
            if (data["current"] != null) status.Text = "正在处理第 " + data["current"] + " 关 · 本次已确认 " + count + " 关三星";
        } catch (IOException) {} catch (ArgumentException) {} catch (KeyNotFoundException) {}
    }
}

static class Runner {
    public static ProcessStartInfo Info(string root, string arguments) {
        var info = new ProcessStartInfo(Path.Combine(root, "engine", ".env", "python.exe"));
        info.Arguments = "\"" + Path.Combine(root, "app", "run_event_missions.py") + "\" " + arguments;
        info.WorkingDirectory = root; info.UseShellExecute = false; info.CreateNoWindow = true;
        info.RedirectStandardOutput = info.RedirectStandardError = true;
        info.StandardOutputEncoding = info.StandardErrorEncoding = Encoding.UTF8;
        info.EnvironmentVariables["PYTHONUTF8"] = "1";
        info.EnvironmentVariables["PYTHONIOENCODING"] = "utf-8";
        return info;
    }
    [STAThread]
    static int Main(string[] args) {
        string root = AppDomain.CurrentDomain.BaseDirectory;
        if (args.Length == 1 && args[0] == "--self-test") {
            var process = new Process { StartInfo = Info(root, "--verify-libraries") };
            var errors = new StringBuilder();
            process.ErrorDataReceived += delegate(object s, DataReceivedEventArgs e) { if (e.Data != null) errors.AppendLine(e.Data); };
            process.Start(); process.BeginErrorReadLine();
            string result = process.StandardOutput.ReadToEnd(); process.WaitForExit();
            File.WriteAllText(Path.Combine(root, "launcher-check.json"), result, Encoding.UTF8);
            File.WriteAllText(Path.Combine(root, "launcher-check.log"), errors.ToString(), Encoding.UTF8);
            return process.ExitCode;
        }
        bool created;
        using (var mutex = new Mutex(true, "Local\\BAEventMissionsPortable", out created)) {
            if (!created) { MessageBox.Show("任务助手已经打开，请使用已有窗口。", "活动任务助手"); return 1; }
            Application.EnableVisualStyles(); Application.SetCompatibleTextRenderingDefault(false);
            Application.Run(new MissionWindow());
        }
        return 0;
    }
}
