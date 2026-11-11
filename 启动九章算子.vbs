' Jiuzhang Operator - silent launcher (double-click this file).
' Runs start.bat with a hidden console window, so no black window ever shows up.
' start.bat itself polls /healthz in a hidden helper and opens the browser
' once the server is actually serving.

Option Explicit

Dim fso, shell, here, target, quote

Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")

here = fso.GetParentFolderName(WScript.ScriptFullName)
target = here & "\start.bat"

If Not fso.FileExists(target) Then
  MsgBox "start.bat was not found next to this launcher." & vbCrLf & _
         "Please keep both files in the same folder.", 16, "Jiuzhang Operator"
  WScript.Quit 1
End If

shell.CurrentDirectory = here
quote = Chr(34)
' Window style 0 = hidden console; wait=False lets this launcher exit at once.
shell.Run "cmd /c " & quote & quote & target & quote & quote, 0, False
