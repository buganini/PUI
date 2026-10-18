"""Optional coding agents; SDKs are loaded only when a prompt is submitted."""
import importlib.util
import logging


def enabled_providers(codex=None, claude=None):
    result = {}
    for name, value, package in (('codex', codex, 'openai_codex'),
                                 ('claude', claude, 'claude_agent_sdk')):
        if value is None or value is False:
            continue
        if not isinstance(value, dict):
            raise ValueError(name + ' must be a dict or None/False')
        if value.keys() - {'key', 'model', 'effort'}:
            raise ValueError(name + ' supports only key, model and effort')
        for field, setting in value.items():
            if not isinstance(setting, str) or not setting.strip():
                raise ValueError(name + '.' + field + ' must be a nonempty string')
        if importlib.util.find_spec(package) is None:
            raise ImportError("Install qpuiq[" + name + "] to enable this agent")
        result[name] = dict(value)
    return result


def unsupported(backend, codex, claude):
    if any(value is not None and value is not False for value in (codex, claude)):
        logging.getLogger('PUI').warning('%s does not support AI integration', backend)
