from ..base import ToolProvider


class JinhuiErpToolProvider(ToolProvider):

    def __init__(self):
        self._tools = []

    def add_tool(self, tool):
        self._tools.append(tool)

    def get_tools(self):
        return list(self._tools)
