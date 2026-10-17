# AI development: remaining work

- Textual and Pyodide AI interfaces are not implemented; enabled AI options log a warning.
- Native Windows/macOS lifecycle and SDK integration need on-platform validation.
- Real model-driven edit/approval/cancel flows still need live-provider validation.
  The Web Codex sidebar has completed a real text-only prompt; edit/approval/cancel
  regression tests still use fake agents. Claude needs an authenticated test login.
- Arbitrary MCP form schemas do not have dedicated form controls; Codex form
  elicitation uses JSON text. External MCP OAuth/browser authentication is not
  embedded in the AI interface.
