from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import List, Optional
from pydantic import BaseModel, Field, model_validator
from app.llm import LLM
from app.schema import ROLE_TYPE, AgentState, Memory, Message


class BaseAgent(BaseModel, ABC):
    """
    管理智能体状态与执行的抽象基类。
    提供状态转换、内存管理和基于步骤的执行循环的基础功能。子类必须实现step方法。

    """
    name: str = Field(..., description="Unique name of the agent")
    description: Optional[str] = Field(None, description="Optional agent description")

    # Prompts
    system_prompt: Optional[str] = Field(
        None, description="系统提示词"
    )
    next_step_prompt: Optional[str] = Field(
        None, description="下一步提示词"
    )

    # Dependencies
    llm: LLM = Field(default_factory=LLM, description="Language model instance")
    memory: Memory = Field(default_factory=Memory, description="Agent's memory store")
    state: AgentState = Field(
        default=AgentState.IDLE, description="Current agent state"
    )

    # Execution control
    max_steps: int = Field(default=10, description="Maximum steps before termination")
    current_step: int = Field(default=0, description="Current step in execution")

    duplicate_threshold: int = 2

    #验证LLM和Memory是否已经实例化
    
    @model_validator(mode="after")#用于模型验证的装饰器，用处？

    def initialize_agent(self) -> "BaseAgent":
        """如果没有提供初始化agent所需的默认参数"""
        if self.llm is None or not isinstance(self.llm, LLM):
            self.llm = LLM(max_tokens=1024, temperature=0)
        if not isinstance(self.memory, Memory):
            self.memory = Memory()
        return self


    @asynccontextmanager # 异步上下文管理器，用于状态转换 。装饰器？
    async def state_context(self, new_state: AgentState):
        """
        用于安全代理状态转换的上下文管理器。
        Args:
            new_state: The state to transition to during the context.
        Yields:
            None: Allows execution within the new state.
        Raises:
            ValueError: If the new_state is invalid.
        """
        if not isinstance(new_state, AgentState):
            raise ValueError(f"Invalid state: {new_state}")

        previous_state = self.state
        self.state = new_state
        try:
            yield # 在此处暂停，执行用户代码
        except Exception as e:
            self.state = AgentState.ERROR  # Transition to ERROR on failure
            raise e # 重新抛出异常，异常会向上传递
        finally:
            self.state = previous_state  # Revert to previous state

        """
        这段代码定义了一个异步上下文管理器 state_context，用于安全地管理代理（Agent）的状态转换。
        在代码块执行期间临时切换到新状态，执行结束后自动恢复原状态（或在出错时切换到错误状态）。
        """

#这里好像需要用到异步，可能这整个函数都需要被删掉

    def update_memory(
        self,
        role: ROLE_TYPE,  # type: ignore
        content: str,
        **kwargs,
    ) -> None:
        """Add a message to the agent's memory.
        Args:
            role: The role of the message sender (user, system, assistant, tool).
            content: The message content.
            **kwargs: Additional arguments (e.g., tool_call_id for tool messages).
        Raises:
            ValueError: If the role is unsupported.
        """
        message_map = {
            "user": Message.user_message,
            "system": Message.system_message,
            "assistant": Message.assistant_message,
            "tool": lambda content, **kw: Message.tool_message(content, **kw),
        }

        if role not in message_map:
            raise ValueError(f"Unsupported message role: {role}")

        # Create message with appropriate parameters based on role
        kwargs = { **(kwargs if role == "tool" else {})}
        self.memory.add_message(message_map[role](content, **kwargs))

    async def run(self, request: Optional[str] = None) -> str:
        """Execute the agent's main loop asynchronously.
        Args:
            request: Optional initial user request to process.
        Returns:
            A string summarizing the execution results.
        Raises:
            RuntimeError: If the agent is not in IDLE state at start.
        """
        if self.state != AgentState.IDLE:
            raise RuntimeError(f"Cannot run agent from state: {self.state}")

        if request:
            self.update_memory("user", request)

        results: List[str] = []
        async with self.state_context(AgentState.RUNNING):
            while (
                self.current_step < self.max_steps and self.state != AgentState.FINISHED
            ):
                self.current_step += 1
                print(f"Executing step {self.current_step}/{self.max_steps}")
                step_result = await self.step()

                # Check for stuck state
                if self.is_stuck():
                    self.handle_stuck_state()

                results.append(f"Step {self.current_step}: {step_result}")

            if self.current_step >= self.max_steps:
                self.current_step = 0
                self.state = AgentState.IDLE
                results.append(f"Terminated: Reached max steps ({self.max_steps})")
 
        return "\n".join(results) if results else "No steps executed"
    #等价于if results: return "\n".join(results)else: return "No steps executed"
    #"\n".join(results)将 results（假设是一个字符串列表）用换行符 \n 连接成一个字符串。

    @abstractmethod  #抽象方法,子类必须实现
    async def step(self) -> str:
        """Execute a single step in the agent's workflow.

        Must be implemented by subclasses to define specific behavior.
        """

    def handle_stuck_state(self):
        """Handle stuck state by adding a prompt to change strategy"""
        stuck_prompt = "\
        检测到重复响应，请尝试新策略，避免重复已经验证无效的路径"
        self.next_step_prompt = f"{stuck_prompt}\n{self.next_step_prompt}"
        print(f"智能体检测到卡死状态，已添加提示： {stuck_prompt}")

    def is_stuck(self) -> bool:
        """通过检测重复内容，检查智能体是否陷入循环"""
        if len(self.memory.messages) < 2:
            return False

        last_message = self.memory.messages[-1]
        if not last_message.content:
            return False

        # Count identical content occurrences
        duplicate_count = sum(
            1
            for msg in reversed(self.memory.messages[:-1])
            if msg.role == "assistant" and msg.content == last_message.content
        )

        return duplicate_count >= self.duplicate_threshold

    @property
    def messages(self) -> List[Message]:
        """Retrieve a list of messages from the agent's memory."""
        return self.memory.messages

    @messages.setter
    def messages(self, value: List[Message]):
        """Set the list of messages in the agent's memory."""
        self.memory.messages = value
