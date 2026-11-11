' Jiuzhang Operator - silent stop (double-click this file).
' Finds the hidden start.bat that belongs to THIS folder and stops its whole
' process tree (cmd + uvicorn). Nothing else on the machine is touched.

Option Explicit

Dim fso, shell, here, wmi, procs, proc, found

Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")
here = LCase(fso.GetParentFolderName(WScript.ScriptFullName))
Set wmi = GetObject("winmgmts:\\.\root\cimv2")
Set procs = wmi.ExecQuery("SELECT ProcessId, CommandLine FROM Win32_Process WHERE Name='cmd.exe'")

found = 0
For Each proc In procs
  If Not IsNull(proc.CommandLine) Then
    If InStr(1, LCase(proc.CommandLine), "start.bat", vbTextCompare) > 0 Then
      If InStr(1, LCase(proc.CommandLine), here, vbTextCompare) > 0 Then
        shell.Run "taskkill /PID " & proc.ProcessId & " /T /F", 0, True
        found = found + 1
      End If
    End If
  End If
Next

' No dialog: stopping an already stopped app should be a no-op, not a nuisance.
