from langchain_openai.chat_models.base import BaseChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain, SequentialChain,TransformChain
from typing import Dict, Any
import geopandas as gpd
from app.tool.get_buff import query_point_by_name,chang_utm,creat_buff,query_intersection


def querybufferchain(input: str) -> str:

    llm = BaseChatOpenAI(
    model='deepseek-chat', 
    openai_api_key='sk-4661c26f15534abd8e3eb7279c2687e3', 
    openai_api_base='https://api.deepseek.com',
    max_tokens=1024,
    temperature = 0,
    )


    # 自然语言解析链
    def first_step() -> LLMChain:
        # 构建提示词模板
        temple = """请从用户输入中精准提取地理查询参数，遵循以下规则：
        1. 识别用户所需要的目标地点名称（如超市、酒店等）
        2. 解析缓冲距离数值（单位自动转换为米）
        3. 若未明确距离，默认返回500米
        4. 忽略不相关描述内容
        5. 不要加其他任何无关内容和符号，严格按照示例输出
        6. 遇到用户输入括号严格按照示例输出
    

        示例：
        输入：寻找地铁站附近500米的超市
        输出：地铁站500和超市

        输入：我需要找沙口(地铁站)800米内的超市
        输出：沙口(地铁站)800和超市

        输入：{user_input}
        输出："""

        # 构建处理链
        prompt = PromptTemplate(
            template = temple,
            input_variables=["user_input"],
        )

        return LLMChain(
            llm=llm,
            prompt=prompt,
            output_key="geo_params"
        )
    first_chain = first_step()
    #第二个查询链
    def strong_query(inputs: Dict[str, Any]) -> Dict[str, Any]:
        input_str = inputs["geo_params"]     
        shp_files = [
            r"C:\Users\ASUS\Desktop\GeoGPT\inputdata\factory.shp",
            r"C:\Users\ASUS\Desktop\GeoGPT\inputdata\subway.shp",
            r"C:\Users\ASUS\Desktop\GeoGPT\inputdata\supermarket.shp",
            r"C:\Users\ASUS\Desktop\GeoGPT\inputdata\hotel.shp",
        ]
        # 1. 按“和”字拆分字符串
        part1, part2 = input_str.split("和")  # 直接拆分成两部分
        if part2 == "工厂":
            shp_point =gpd.read_file(r"C:\Users\ASUS\Desktop\GeoGPT\inputdata\factory.shp") 
        elif part2 == "地铁站":
            shp_point = gpd.read_file(r"C:\Users\ASUS\Desktop\GeoGPT\inputdata\subway.shp")  
        elif part2 == "超市":
            shp_point = gpd.read_file(r"C:\Users\ASUS\Desktop\GeoGPT\inputdata\supermarket.shp")  
        elif part2 == "宾馆":
            shp_point = gpd.read_file(r"C:\Users\ASUS\Desktop\GeoGPT\inputdata\hotel.shp")  
        """解析单个地点信息"""
        name = ''.join([c for c in part1 if not c.isdigit()])
        distance = int(''.join([c for c in part1 if c.isdigit()]))
        if  name == "工厂":
            shp_point =gpd.read_file(r"C:\Users\ASUS\Desktop\GeoGPT\inputdata\factory.shp") 
        elif name == "地铁站":
            shp_point = gpd.read_file(r"C:\Users\ASUS\Desktop\GeoGPT\inputdata\subway.shp")  
        elif name == "超市":
            shp_point = gpd.read_file(r"C:\Users\ASUS\Desktop\GeoGPT\inputdata\supermarket.shp")  
        elif name == "宾馆":
            shp_point = gpd.read_file(r"C:\Users\ASUS\Desktop\GeoGPT\inputdata\hotel.shp")  
        else :
        # 查询"武昌火车站"
            buffer_path = query_point_by_name(shp_files, name)
        if buffer_path is not None:
            # 创建缓冲区
            buffer_zone =creat_buff(buffer_path,distance)
            
            # 加载需要被查询的点数据
            shp_point =chang_utm(shp_point)
            # 查询缓冲区内的超市
            total_result = query_intersection(shp_point, buffer_zone)

        return {"buffer_result": total_result}
    #第二个缓冲区链

    analysis_chain = TransformChain(
        input_variables=["geo_params"],  # 接收前序链的输出
        output_variables=["buffer_result"],
        transform=strong_query,
        verbose=True  # 显示处理细节
    )

    from langchain.chains import  SequentialChain
    # 组合并行链和合并链
    combined_chain = SequentialChain(
        chains=[first_chain, analysis_chain],
        input_variables=["user_input"],
        output_variables=["buffer_result"],
        verbose=True
    )

    result = combined_chain.invoke(input)
    print(f"共查询到{result}条结果符合要求")


