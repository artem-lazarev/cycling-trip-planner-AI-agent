import logging
import re

from tools import ALL_TOOLS
from prompts import SYSTEM_PROMPT, TEST_PROMPT

from anthropic import Anthropic

MODEL_NAME = "claude-sonnet-4-6"
MAX_TOKENS = 4096

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    handlers=[logging.FileHandler("agent.log")],
)

logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

# Strip <scratch>...</scratch> blocks (the model uses these for private
# reasoning per the system prompt). The `(?:</scratch>|$)` branch handles
# unclosed tags (e.g. when output is truncated at MAX_TOKENS) so trailing
# reasoning doesn't leak to the user.
_SCRATCH_RE = re.compile(
    r"<scratch>.*?(?:</scratch>|$)\s*", re.DOTALL | re.IGNORECASE
)


class AIAgent:
    def __init__(self, api_key):
        self.client = Anthropic(api_key=api_key)
        self.messages = []
        self.tool_definitions = [tool.DEFINITION for tool in ALL_TOOLS]

    def _execute_tool(self, tool_name, tool_input):
        logging.info(f"Executing tool: {tool_name} with input: {tool_input}")
        try:
            for tool in ALL_TOOLS:
                if tool.DEFINITION["name"] == tool_name:
                    return tool.execute(tool_input)
            return f"Unknown tool: {tool_name}"
        except Exception as e:
            logging.error(f"Error executing {tool_name}: {str(e)}")
            return f"Error executing {tool_name}: {str(e)}"

    def chat(self, user_input):
        logging.info(f"User input: {user_input}")
        self.messages.append({"role": "user", "content": user_input})

        # Tool-calling loop: Claude may want to call tools across multiple turns
        # before producing a final text reply. We keep looping until it stops
        # asking for tool calls.
        while True:
            response = self.client.messages.create(
                model=MODEL_NAME,
                max_tokens=MAX_TOKENS,
                system=TEST_PROMPT,
                messages=self.messages,
                tools=self.tool_definitions,
            )

            # Mirror the assistant's content back into our message history so
            # the next turn has the full context (including any tool_use blocks).
            assistant_content = []
            for block in response.content:
                if block.type == "text":
                    assistant_content.append({"type": "text", "text": block.text})
                elif block.type == "tool_use":
                    assistant_content.append({
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    })
            self.messages.append({"role": "assistant", "content": assistant_content})

            # Run any requested tool calls and feed their results back as a
            # user-role message containing tool_result blocks.
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = self._execute_tool(block.name, block.input)
                    logging.info(f"Tool result: {str(result)[:500]}...")
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            if tool_results:
                self.messages.append({"role": "user", "content": tool_results})
                continue

            # No more tool calls -> this is the final assistant turn. Return all
            # text blocks concatenated (there can be more than one), with any
            # <scratch>...</scratch> reasoning sections removed.
            text_parts = [b.text for b in response.content if b.type == "text"]
            reply = "\n".join(text_parts)
            return _SCRATCH_RE.sub("", reply).strip()
