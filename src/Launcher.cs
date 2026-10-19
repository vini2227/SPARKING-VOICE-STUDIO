using System;
using System.Diagnostics;
using System.IO;
using System.Windows.Forms;
class VoiceStudioLauncher {
 [STAThread] static void Main() {
  try {
   string root=AppDomain.CurrentDomain.BaseDirectory;
   string python=Path.Combine(root,"Runtime","pythonw.exe");
   if (!File.Exists(python)) {
    python=File.ReadAllText(Path.Combine(root,"runtime.path")).Trim();
    if (!Path.IsPathRooted(python)) python=Path.GetFullPath(Path.Combine(root,python));
   }
   if (!File.Exists(python)) throw new Exception("Bundled Python was not found. Extract the entire ZIP again, including the Runtime folder.");
   var p=new ProcessStartInfo(python,"-B \""+Path.Combine(root,"src","app.py")+"\"");
   p.WorkingDirectory=root;p.UseShellExecute=false;p.CreateNoWindow=true;
   Process.Start(p);
  } catch(Exception ex) { MessageBox.Show(ex.Message,"Sparking Zero Voice Studio",MessageBoxButtons.OK,MessageBoxIcon.Error); }
 }
}