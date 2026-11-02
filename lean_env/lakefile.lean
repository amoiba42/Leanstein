import Lake
open Lake DSL

-- Pinned verification environment for the study. Versions match VERINA's
-- supported v4.24 configuration (third_party/verina/setup_lean_v424.sh).
package «prl» where
  leanOptions := #[⟨`pp.unicode.fun, true⟩]

require mathlib from git "https://github.com/leanprover-community/mathlib4.git" @ "v4.24.0"

@[default_target]
lean_lib «Prl» where

-- PRL verification server: imports Mathlib once, elaborates many files (see PrlRepl.lean).
lean_exe prlrepl where
  root := `PrlRepl
  supportInterpreter := true
