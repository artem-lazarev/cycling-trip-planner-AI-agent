from tools import ALL_TOOLS
from prompts import SYSTEM_PROMPT

from anthropic import Anthropic

MODEL_NAME = "claude-sonnet-4-6"
MAX_TOKENS = 4096

class AIAgent:
    def __init__(self, api_key):
        self.client = Anthropic(api_key=api_key)
        self.messages = []

    def _execute_tool(self, tool_name, tool_input):
        for tool in ALL_TOOLS:
            if tool.DEFINITION["name"] == tool_name:
                return tool.execute(tool_input)
        return f"Unknown tool: {tool_name}"

    def chat(self, user_input):
        self.messages.append({"role": "user", "content": user_input})

        tool_definitions = [tool.DEFINITION for tool in ALL_TOOLS]

        while True:
            try:
                response = self.client.messages.create(
                    model=MODEL_NAME,
                    max_tokens=MAX_TOKENS,
                    system=SYSTEM_PROMPT,
                    messages=self.messages,
                    tools=tool_definitions,
                )

                assistant_message = {"role": "assistant", "content": []}

                for content in response.content:
                    if content.type == "text":
                        assistant_message["content"].append(
                            {"type": "text", "text": content.text}
                        )
                    elif content.type == "tool_use":
                        assistant_message["content"].append(
                            {
                                "type": "tool_use",
                                "id": content.id,
                                "name": content.name,
                                "input": content.input,
                            }
                        )

                self.messages.append(assistant_message)

                tool_results = []
                for content in response.content:
                    if content.type == "tool_use":
                        result = self._execute_tool(content.name, content.input)
                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": content.id,
                                "content": result,
                            }
                        )

                if tool_results:
                    self.messages.append({"role": "user", "content": tool_results})
                else:
                    return response.content[0].text if response.content else ""

            except Exception as e:
                return f"Error: {str(e)}"


