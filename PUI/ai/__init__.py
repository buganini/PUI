"""Optional coding agents; SDKs are loaded only when a prompt is submitted."""
import importlib.util
import logging


def enabled_providers(codex=None, claude=None):
    result = {}
    for name, value, package in (('codex', codex, 'openai_codex'),
                                 ('claude', claude, 'claude_agent_sdk')):
        if value is None or value is False:
            continue
        if value is not True and (not isinstance(value, str) or not value.strip()):
            raise ValueError(name + ' must be True, an API key, or None/False')
        if importlib.util.find_spec(package) is None:
            raise ImportError("Install qpuiq[" + name + "] to enable this agent")
        result[name] = value
    return result


def unsupported(backend, codex, claude):
    if codex or claude:
        logging.getLogger('PUI').warning('%s does not support AI integration', backend)
