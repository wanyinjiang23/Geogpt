"""Execute the original agent in a killable process, never on the API loop."""
import asyncio
import os
from pathlib import Path


def run_agent(connection, prompt, memory, context):
    os.chdir(Path(__file__).resolve().parents[2])
    os.environ.setdefault("MPLBACKEND", "Agg")
    try:
        from app.Agent.gis_agent import GISAgent
        from app.schema import Message

        class WebGISAgent(GISAgent):
            async def step(self):
                connection.send({"type": "progress", "text": f"正在执行第 {self.current_step} 步"})
                result = await super().step()
                connection.send({"type": "progress", "text": result})
                return result

        agent = WebGISAgent()
        agent.memory.messages = [Message.model_validate(message) for message in memory]
        for name, value in context.items():
            setattr(agent, name, value)
        summary = asyncio.run(agent.run(prompt))
        answers = [m.content for m in agent.messages[len(memory):]
                   if m.role == "assistant" and m.content and not m.tool_calls]
        connection.send({"type": "done", "text": answers[-1] if answers else summary,
                         "memory": [m.model_dump(mode="json") for m in agent.messages],
                         "context": {name: getattr(agent, name) for name in
                                     ("_current_shapefile", "_current_buffer")}})
    except BaseException as error:
        # Avoid sending provider exception bodies (which may contain credentials).
        if isinstance(error, ModuleNotFoundError):
            message = f"后端缺少依赖 {error.name}，请安装 requirements-web.txt。"
        else:
            message = f"后端执行失败（{type(error).__name__}），请检查模型配置及输入数据。"
        connection.send({"type": "error", "text": message})
    finally:
        connection.close()
