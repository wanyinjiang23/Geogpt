from app.tool.base import BaseTool, ToolResult, CLIResult, ToolFailure

# Keep the lightweight contracts usable without importing encrypted legacy modules.
def __getattr__(name):
    from importlib import import_module
    modules = {"CreateChatCompletion": "create_chat_completion", "Terminate": "terminate",
               "ToolCollection": "tool_collection"}
    if name in modules:
        return getattr(import_module(f"app.tool.{modules[name]}"), name)
    raise AttributeError(name)

__all__ = [
    'BaseTool', 
    'ToolResult', 
    'CLIResult', 
    'ToolFailure', 
    'CreateChatCompletion',
    'Terminate',
    'ToolCollection',
] 
