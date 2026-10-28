from typing import Any, List, Optional, Type, Union, get_args, get_origin, Dict
from pydantic import BaseModel, Field
from app.tool import BaseTool

#将聊天模型的输出按预定义的类型（如 str、BaseModel、List 等）进行结构化转换和验证。
#强制模型输出符合特定格式（如JSON Schema）

class CreateChatCompletion(BaseTool):
    name: str = "create_chat_completion"
    description: str = (
        "Creates a structured completion with specified output formatting."
    )

    # Type mapping for JSON schema
    type_mapping: dict = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
        dict: "object",
        list: "array",
    }
    #指定输出的目标类型
    response_type: Optional[Type] = None
    #必填字段列表
    required: List[str] = Field(default_factory=lambda: ["response"])
    parameters: Dict[str, Any] = Field(default_factory=dict)

    def __init__(self, response_type: Optional[Type] = str):
        """Initialize with a specific response type."""
        super().__init__()
        self.response_type = response_type
        #basetool的属性
        #调用当前对象的 _build_parameters() 方法，并将其返回值赋给 self.parameters 属性​​
        self.parameters = self._build_parameters()
#根据 response_type 生成JSON Schema，描述输出结构
    def _build_parameters(self) -> dict:
        """Build parameters schema based on response type."""
        #处理str类型
        if self.response_type == str:
            return {
                "type": "object",
                "properties": {
                    "response": {
                        "type": "string",
                        "description": "The response text that should be delivered to the user.",
                    },
                },
                "required": self.required,
            }
        #处理 Pydantic 模型BaseModel子类
        if isinstance(self.response_type, type) and issubclass(
            self.response_type, BaseModel
        ):
            schema = self.response_type.model_json_schema()
            return {
                "type": "object",
                "properties": schema["properties"],
                "required": schema.get("required", self.required),
            }
        #处理其他复杂类型
        return self._create_type_schema(self.response_type)

    def _create_type_schema(self, type_hint: Type) -> dict:
        """Create a JSON schema for the given type."""
        #get_origin是父类的方法
        #对于简单类型（如 str, int），返回 None。对于泛型或参数化类型（如 List[int], Dict[str, float]），返回其原始容器类型（如 list, dict）。
        origin = get_origin(type_hint)
        #对于简单类型或无参数的类型，返回空元组 ()。对于泛型类型，返回其类型参数的元组（如 (int,)、(str, int)
        args = get_args(type_hint)

        # Handle primitive types 表示非泛型类型（如 str, int, bool）
        #处理前面定义的字典中有的类型
        if origin is None:
            return {
                "type": "object",
                "properties": {
                    "response": {
                        #从 type_mapping 字典中查找 type_hint 对应的值
                        "type": self.type_mapping.get(type_hint, "string"),
                        #是 Python 类型的内置属性，返回类型的名称（字符串形式）,对于泛型返回原始属性
                        "description": f"Response of type {type_hint.__name__}",
                    }
                },
                "required": self.required,
            }

        # Handle List type
        #处理泛型列表类型
        if origin is list:
            #从泛型类型的参数（args）中获取第一个类型参数（即容器元素的类型），如果参数不存在则默认返回 Any 类型。
            item_type = args[0] if args else Any
            return {
                "type": "object",
                "properties": {
                    "response": {
                        "type": "array",
                        "items": self._get_type_info(item_type),
                    }
                },
                "required": self.required,
            }

        # Handle Dict type
        #处理字典
        if origin is dict:
            value_type = args[1] if len(args) > 1 else Any
            return {
                "type": "object",
                "properties": {
                    "response": {
                        "type": "object",
                        "additionalProperties": self._get_type_info(value_type),
                    }
                },
                "required": self.required,
            }

        # Handle Union type
        #处理Union类型
        if origin is Union:
            return self._create_union_schema(args)

        return self._build_parameters()
#为单个 Python 类型生成对应的类型信息字典，主要用于构建 JSON Schema 或类型描述
    def _get_type_info(self, type_hint: Type) -> dict:
        """Get type information for a single type."""
        #处理单个类型
        if isinstance(type_hint, type) and issubclass(type_hint, BaseModel):
            return type_hint.model_json_schema()
            # ​model_json_schema()​将 Pydantic/BaseModel 类转换为 JSON Schema​
        return {
            "type": self.type_mapping.get(type_hint, "string"),
            "description": f"Value of type {getattr(type_hint, '__name__', 'any')}",
        }
#处理Union类型
    def _create_union_schema(self, types: tuple) -> dict:
        """Create schema for Union types."""
        return {
            "type": "object",
            "properties": {
                "response": {"anyOf": [self._get_type_info(t) for t in types]}
            },
            "required": self.required,
        }

    async def execute(self, required: list | None = None, **kwargs) -> Any:
        """Execute the chat completion with type conversion.

        Args:
            required: List of required field names or None
            **kwargs: Response data

        Returns:
            Converted response based on response_type
        """
        # 优先使用传入的required，否则用self.required
        required = required or self.required
        #​​情况1​​：required 是单元素列表，提取 kwargs 中该字段的值，若不存在则返回空字符串 ""
        # Handle case when required is a list
        if isinstance(required, list) and len(required) > 0:
            if len(required) == 1:
                required_field = required[0]
                result = kwargs.get(required_field, "")
            else:
                #​情况2​：required 是多元素列表，返回包含所有字段的字典，缺失字段赋值为 ""
                # Return multiple fields as a dictionary
                return {field: kwargs.get(field, "") for field in required}
        #情况3：required 为空或 None默认提取 kwargs 中的 "response" 字段：
        else:
            required_field = "response"
            result = kwargs.get(required_field, "")
            
        #根据 self.response_type 的类型决定如何转换 result
        # Type conversion logic
        if self.response_type == str:
            return result

        if isinstance(self.response_type, type) and issubclass(
            self.response_type, BaseModel
        ):
            return self.response_type(**kwargs)

        if get_origin(self.response_type) in (list, dict):
            return result  # Assuming result is already in correct format

        try:
            return self.response_type(result)
        except (ValueError, TypeError):
            return result

#上面的几个函数都是将相应的数据类型构建为JSON Schema 
"""​​JSON Schema​​ 是一种用于描述和验证 JSON 数据结构的标准格式，
类似于数据库的表结构定义或编程语言中的类型声明。
它的核心作用是 ​​为JSON数据提供明确的规则和约束​​，确保数据格式的正确性和一致性。
"""

#required是类中定义的必须传入的字段
