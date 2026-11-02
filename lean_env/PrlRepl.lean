/-
PRL verification server (our own code; uses only Lean core APIs).

Imports `Mathlib` ONCE, then repeatedly reads one request line from stdin: the path of a Lean file.
The file's header (`import ...` lines) is skipped; its commands are elaborated against a *fresh copy*
of the pre-imported environment (environments are immutable values, so every request starts from the
same state — determinism is preserved). For each request it prints exactly one JSON line:
  {"ok": true, "messages": [{"line": L, "col": C, "severity": "error|warning|information", "text": "..."}]}
-/
import Lean
open Lean Elab

def sevStr : MessageSeverity → String
  | .error => "error"
  | .warning => "warning"
  | .information => "information"

def processFile (env : Environment) (opts : Options) (path : System.FilePath) : IO Json := do
  let input ← IO.FS.readFile path
  let inputCtx := Parser.mkInputContext input path.toString
  let (_, parserState, headerMsgs) ← Parser.parseHeader inputCtx
  let cmdState := Command.mkState env headerMsgs opts
  let s ← IO.processCommands inputCtx parserState cmdState
  let msgs := s.commandState.messages.toList
  let mut arr : Array Json := #[]
  for m in msgs do
    let txt ← m.data.toString
    arr := arr.push <| Json.mkObj [
      ("line", Json.num m.pos.line), ("col", Json.num m.pos.column),
      ("severity", Json.str (sevStr m.severity)), ("text", Json.str txt)]
  return Json.mkObj [("ok", Json.bool true), ("messages", Json.arr arr)]

unsafe def main (args : List String) : IO UInt32 := do
  let mods := if args.isEmpty then [`Mathlib] else args.map String.toName
  initSearchPath (← findSysroot)
  enableInitializersExecution
  let env ← importModules (mods.toArray.map ({ module := · })) {} (trustLevel := 1024) (loadExts := true)
  let opts : Options := ({} : Options) |>.setBool `Elab.async false
  let stdin ← IO.getStdin
  let stdout ← IO.getStdout
  stdout.putStrLn "{\"ready\": true}"
  stdout.flush
  repeat
    let line ← stdin.getLine
    if line.isEmpty then break
    let p := line.trim
    if p.isEmpty then continue
    let res ← try processFile env opts p catch e =>
      pure (Json.mkObj [("ok", Json.bool false), ("error", Json.str (toString e))])
    stdout.putStrLn res.compress
    stdout.flush
  return 0
