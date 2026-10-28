import rasterio
import numpy as np
from scipy.ndimage import sobel
import matplotlib.pyplot as plt
from matplotlib.colors import hsv_to_rgb
from matplotlib.colors import Normalize
from rasterio.crs import CRS
from rasterio.warp import calculate_default_transform, reproject, Resampling
import os
from shapely.geometry import mapping
from scipy.spatial.distance import cdist
from rasterio.transform import from_origin
from rasterio.mask import mask
from pyproj import CRS

from typing import Optional, Dict, Any, ClassVar
import geopandas as gpd
from pathlib import Path
from app.tool.base import BaseTool, ToolResult, CLIResult, ToolFailure
import folium
import geopandas as gpd
from app.tool.base import BaseTool, ToolResult
from app.tool.get_buff import (
    buffer_analysis,
    chang_utm,
    compute_buffer_difference,
    compute_buffer_intersection,
    compute_buffer_union,
    query_intersection,
    query_point_by_name,
    creat_buff
)

from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import OpenAIEmbeddings
from langchain.chains import RetrievalQA
from langchain_openai import OpenAI 

class QAchainTool(BaseTool):
    """Tool for reading and validating shapefiles based on keywords"""
    
    name: str = "QAchain"
    description: str = "获取焦作市相关地理信息，如焦作市POI数据文件路径"
    
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "用户输入的问题"
            }
        },
        "required": ["question"]
    }
    
    async def execute(self, question: str) -> str:
      # 文件路径
        file_path = "C:/Users/ASUS/Desktop/jz.txt"
        # 加载最简单的文本文件，其中返回的data为一个Document对象列表
        loader = TextLoader(file_path, encoding='utf-8')
        data = loader.load()
                
        # 文档分割
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=100, chunk_overlap=0)
        #这里split_docs返回的是一个分割后的Document对象列表
        split_docs = text_splitter.split_documents(data)
                

        embeddings = OpenAIEmbeddings(
            openai_api_key="sk-TT8DFlIRf13d249289c1T3BLbkFJE0A6cF589BeD464181de", 
            base_url="https://api.ohmygpt.com/v1", 
            model="text-embedding-ada-002")


        texts = [doc.page_content for doc in split_docs]
        #创建向量数据库
        db = FAISS.from_texts(texts,embeddings)
        retriever = db.as_retriever()

    
        llm = OpenAI(
            openai_api_key="sk-TT8DFlIRf13d249289c1T3BLbkFJE0A6cF589BeD464181de", 
            base_url="https://api.ohmygpt.com/v1", 
            temperature=0.9)
        qa = RetrievalQA.from_chain_type(llm=llm, retriever=retriever)
        resultQA = qa.run(question)
        print(resultQA)
        return ToolResult(output=resultQA)

class CreateBufferTool(BaseTool):
    """创建某个地点的缓冲区范围"""
    
    name: str = "creat_buffer"
    description: str = "创建POI数据的缓冲区"
    
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "input_file": {
                "type": "string",
                "description": "输入的POI数据文件路径"
            },
            "buffer_distance": {
                "type": "number",
                "description": "用户输入的缓冲区距离"
            },
            "output_file": {
                "type": "string",
                "description": "自动生成的保存路径，格式为：data/{地点}_buffer_{距离}.shp（示例：data/supermarket_buffer_500.shp）"
            }
        },
        "required": ["input_file", "buffer_distance", "output_file"]
    }
    
    async def execute(self, input_file: str, buffer_distance: float, output_file: str) -> ToolResult:
        gdf = gpd.read_file(input_file)
        
        
        analysis_result = buffer_analysis(
            gdf=gdf,
            buffer_distance=buffer_distance,
            output_path=str(output_file)
        )
        result = analysis_result
        
        return ToolResult(output=result)
class IntersectionAnalysisTool(BaseTool):
    """对两个缓冲区进行叠加处理"""
    
    name: str = "intersection_analysis"
    description: str = "对输入的两个shp缓冲区文件求交集"
    
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "input_file1": {
                "type": "string",
                "description": "输入的第一个shp缓冲区文件路径"
            },
            "input_file2": {
                "type": "string",
                "description": "输入的第二个shp缓冲区文件路径"
            },
            "output_file": {
                "type": "string",
                "description": "自动生成的保存路径，格式为：data/{地点1}_{叠加类型}_{地点2}m.shp（示例：data/supermarket_inter_factory.shp）"
            }
        },
        "required": ["input_file1", "input_file2",  "output_file"]
    }
    
    async def execute(self, input_file1: str, input_file2: str,  output_file: str) -> ToolResult:
        
        result = compute_buffer_intersection(input_file1,input_file2,output_file)
            
        return ToolResult(output=result)  
class UnionAnalysisTool(BaseTool):
    """对两个缓冲区进行联合处理"""
    
    name: str = "union_analysis"
    description: str = "对输入的两个shp缓冲区文件求并集"
    
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "input_file1": {
                "type": "string",
                "description": "输入的第一个shp缓冲区文件路径"
            },
            "input_file2": {
                "type": "string",
                "description": "输入的第二个shp缓冲区文件路径"
            },
            "output_file": {
                "type": "string",
                "description": "自动生成的保存路径，格式为：data/{地点1}_union_{地点2}m.shp（示例：data/supermarket_union_factory.shp）"
            }
        },
        "required": ["input_file1", "input_file2",  "output_file"]
    }
    
    async def execute(self, input_file1: str, input_file2: str,  output_file: str) -> ToolResult:
        
        result = compute_buffer_union(input_file1,input_file2,output_file)
            
        return ToolResult(output=result)
class DifferenceAnalysisTool(BaseTool):
    """对两个缓冲区进行擦除处理"""
    
    name: str = "difference_analysis"
    description: str = "需要生成两个缓冲区范围的差集（A - B）"
    
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "input_file1": {
                "type": "string",
                "description": "需要保留的缓冲区范围，差集（A-B）中的A"
            },
            "input_file2": {
                "type": "string",
                "description": "需要被擦除的缓冲区范围，差集（A-B）中的B"
            },
            "output_file": {
                "type": "string",
                "description": "自动生成的保存路径，格式为：data/{保留的地点}_{叠加类型}_{被擦除的地点}m.shp（示例：data/supermarket_differ_factory.shp）"
            }
        },
        "required": ["input_file1", "input_file2",  "output_file"]
    }
    
    async def execute(self, input_file1: str, input_file2: str,  output_file: str) -> ToolResult:
        
        result = compute_buffer_difference(input_file1,input_file2,output_file)
            
        return ToolResult(output=result)

class DrawMapTool(BaseTool):
    """为shp文件添加底图，并通过html进行可视化展示"""
    name: str = "draw_map"
    description: str = "为shp文件添加底图，并通过html进行可视化展示"
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "input_files": {
                "type": "array",
                "items": {
                    "type": "string",
                    "description": "需要可视化的shp文件路径"
                },
                "description": "需要可视化的shp文件路径列表"
            },
            "output_file": {
                "type": "string",
                "description": "输出的html可视化地图文件，格式为：data/{shp文件名}.html（示例：data/supermarket_buffer_800.html）"
            }
        },
        "required": ["input_files", "output_file"]
    }

    async def execute(self, **kwargs) -> ToolResult:
        input_files = kwargs.get("input_files", [])
        output_file = kwargs.get("output_file")

        if not input_files or not output_file:
            return ToolFailure(error="Missing required parameters: input_files or output_file")

        # 1. 确定地图中心点
        default_location = [39.9042, 116.4074]  # 默认北京市经纬度
        if input_files:
            try:
                # 读取第一个文件以确定中心点
                gdf = gpd.read_file(input_files[0])
                gdf = gdf.to_crs(epsg=4326)  # 转换为 WGS84 坐标系
                centroid = gdf.geometry.centroid.iloc[0]
                location = [centroid.y, centroid.x]  # 使用第一个文件的中心点
            except Exception as e:
                print(f"Failed to determine center point from first file: {str(e)}")
                location = default_location  # 如果失败，使用默认中心点
        else:
            location = default_location  # 如果没有文件，使用默认中心点

        # 2. 创建 Folium 地图对象
        m = folium.Map(location=location, zoom_start=10, tiles="OpenStreetMap")

        for input_file in input_files:
            try:
                # 读取 SHP 文件（需为 WGS84 坐标系，EPSG:4326）
                gdf = gpd.read_file(input_file)
                gdf = gdf.to_crs(epsg=4326)  # Folium 要求 WGS84

                # 判断要素类型并处理
                if gdf.geom_type.iloc[0] == 'Point':
                    # 对于点要素，使用 folium.Marker 添加点击事件
                    for _, row in gdf.iterrows():
                        point = row.geometry
                        lat, lon = point.y, point.x
                        # 动态生成弹窗内容，根据点要素的属性表动态生成
                        popup_content = "<br>".join([f"<b>{k}:</b> {v}" for k, v in row.items() if k != 'geometry'])
                        folium.Marker(
                            location=[lat, lon],
                            popup=folium.Popup(popup_content, max_width=300),
                            icon=folium.Icon(color="blue", icon="info-sign")
                        ).add_to(m)
                else:
                    # 对于非点要素，保持原有逻辑
                    folium.GeoJson(
                        gdf,
                        style_function=lambda x: {"fillColor": "blue", "color": "black", "weight": 1},
                    ).add_to(m)
            except Exception as e:
                return ToolFailure(error=f"Error processing file {input_file}: {str(e)}")

        # 3. 保存为 HTML 文件
        try:
            m.save(output_file)
            return ToolResult(output=f"Map saved to {output_file}")
        except Exception as e:
            return ToolFailure(error=f"Error saving map to {output_file}: {str(e)}")
class QuerybufferTool(BaseTool):
    """Tool for performing overlay analysis between two shapefiles"""
    
    name: str = "query_analysis"
    description: str = "查询某个地点的周边范围内相关类型点要素，如查询武昌火车站附近500米的宾馆"
    
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {           
            "keyword": {
                "type": "string",
                "description": "需要生成缓冲区的地点名称，如用户输入查询焦作火车站附近500米的宾馆，则输入焦作火车站"
            },
            "distance": {
                "type": "number",
                "description": "需要生成缓冲区的距离，如用户输入查询焦作火车站附近500米的宾馆，则输入500"
            },
            "input_file1": {
                "type": "string",
                "description": "需要生成缓冲区的POI数据文件路径，如keyword为焦作火车站，则传入焦作火车站可能在的POI数据文件路径，传入traffic.shp"
            },
            "input_file2": {
                "type": "string",
                "description": "用户需要查询的设施点POI数据文件路径"
            },
            "output_file": {
                "type": "string",
                "description": "输出的查询结果点要素shp文件，格式为：data/{周边范围}_querypoint_{目的地类型}.shp（示例：data/沙口(地铁站)500_querypoint_hotel.shp）"
            }
        },
        "required": ["keyword","distance","input_file1","input_file2","output_file"]
    }
    
    async def execute(self, keyword: str, distance:int,input_file1:str,input_file2,output_file:str) -> ToolResult:
        #处理输入的关键字，转换为点的shp对象，为后续生成缓冲区做准备
        keyword_to_path = ["景点","交通设施","医院","宾馆","学校","银行","快递站","超市","餐厅"]
        if keyword not in keyword_to_path:
            try:
        # 尝试查询地点
                gdf = query_point_by_name(keyword, input_file1,name_field='名称')
        
        # 检查返回结果是否为空
                if gdf is None or gdf.empty:
                    raise ValueError(f"未找到地点 '{keyword}' 对应的shapefile")
            
            except Exception as e:
        # 捕获查询过程中的任何异常
                raise ValueError(f"查询地点 '{keyword}' 失败: {str(e)}") from e
        else :
            gdf = gpd.read_file(input_file1)

        #处理需要生成的缓冲区
        shp_buffer = creat_buff(gdf, distance)

        #处理需要被查询的设施点
        shp_point = gpd.read_file(input_file2)
        shp_point =chang_utm(shp_point)
        

        result = query_intersection(shp_point,shp_buffer,output_file)
        
        return ToolResult(output=result)       
class CalculateSlopeTool(BaseTool):
    """对输入的DEM数据计算坡度"""
    
    name: str = "calculate_slope"
    description: str = "对输入的DEM数据计算坡度"
    
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "input_file": {
                "type": "string",
                "description": "输入的DEM数据，用于计算坡度"
            },
            "output_file": {
                "type": "string",
                "description": "输出的坡度数据，格式为：data/{input_file}_slope.tif"
            }
        },
        "required": ["input_file",  "output_file"]
    }
    
    async def execute(self, input_file: str,output_file: str) -> ToolResult:
        def is_geographic_crs(crs):
            """检查是否为地理坐标系（经纬度）"""
            if crs is None:
                return False
            return crs.is_geographic
        
        def reproject_to_utm(dem_path):
            """将DEM重新投影到UTM坐标系（如果当前是地理坐标系）"""
            with rasterio.open(dem_path) as src:
                if not is_geographic_crs(src.crs):
                    return dem_path  # 已经是投影坐标系，无需转换
                
                # 确定合适的UTM投影
                bounds = src.bounds
                utm_crs = CRS.from_epsg(32600 + int((bounds.left + bounds.right) / 2 / 6 + 31))
                
                # 创建临时文件路径
                import tempfile
                import os
                temp_dir = tempfile.mkdtemp()
                reprojected_path = os.path.join(temp_dir, "reprojected_dem.tif")
                
                # 执行重投影
                transform, width, height = calculate_default_transform(
                    src.crs, utm_crs, src.width, src.height, *src.bounds)
                
                profile = src.profile.copy()
                profile.update({
                    'crs': utm_crs,
                    'transform': transform,
                    'width': width,
                    'height': height
                })
                
                with rasterio.open(reprojected_path, 'w', **profile) as dst:
                    reproject(
                        source=rasterio.band(src, 1),
                        destination=rasterio.band(dst, 1),
                        src_transform=src.transform,
                        src_crs=src.crs,
                        dst_transform=transform,
                        dst_crs=utm_crs,
                        resampling=Resampling.bilinear)
                
                return reprojected_path



        def calculate_slope(dem, pixel_size):
            """改进的坡度计算函数，包含边缘处理"""
            # 处理无效值
            dem = np.where(dem == src.nodata, np.nan, dem)
            
            # 计算梯度
            dx = sobel(dem, axis=1, mode='constant', cval=np.nan)
            dy = sobel(dem, axis=0, mode='constant', cval=np.nan)
            
            # 计算坡度
            with np.errstate(invalid='ignore'):
                slope_rad = np.arctan(np.sqrt(dx**2 + dy**2) / (8 * pixel_size))
                slope_deg = np.degrees(slope_rad)
            
            # 保留原始无效值
            slope_deg = np.where(np.isnan(dem), np.nan, slope_deg)
            return slope_deg

        # 检查并转换坐标系
        reprojected_path = reproject_to_utm(input_file)
        is_temp_file = reprojected_path != input_file
        # 读取DEM数据
        try:
            # 读取DEM数据（可能是原始文件或临时重投影文件）
            with rasterio.open(reprojected_path) as src:
                dem = src.read(1)
                transform = src.transform
                crs = src.crs
                bounds = src.bounds
                nodata = src.nodata
                profile = src.profile.copy()

                # 计算坡度
                slope = calculate_slope(dem, pixel_size=transform[0])

                # 增强版栅格输出
                profile.update({
                    'dtype': 'float32',
                    'nodata': np.nan,
                    'count': 1,
                    'compress': 'lzw'
                })

            # 保存坡度结果
                with rasterio.open(output_file, 'w', **profile) as dst:
                    dst.write(slope.astype(np.float32), 1)
                    dst.update_tags(
                        TIFFTAG_IMAGEDESCRIPTION='Slope Map',
                        TIFFTAG_SOFTWARE='Python Rasterio'
                    )
                    dst.set_band_description(1, 'Slope (degrees)')
                
                print(f"坡度计算完成，结果已保存到: {output_file}")
                if is_temp_file:
                    print("注意: 输入DEM已从地理坐标系自动转换为UTM投影坐标系")

        finally:
            # 清理临时文件
            if is_temp_file:
                import os
                os.remove(reprojected_path)
                os.rmdir(os.path.dirname(reprojected_path))
        
        result =output_file

        return ToolResult(output=result)      
class CalculateAspectTool(BaseTool):
    """对输入的DEM数据计算坡向"""
    
    name: str = "calculate_aspect"
    description: str = "对输入的DEM数据计算坡向"
    
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "input_file": {
                "type": "string",
                "description": "输入的DEM数据，用于计算坡向"
            },
            "output_file": {
                "type": "string",
                "description": "输出的坡度数据，格式为：data/{input_file}_aspect.tif"
            }
        },
        "required": ["input_file",  "output_file"]
    }
    
    async def execute(self, input_file: str,output_file: str) -> ToolResult:
        def is_geographic_crs(crs):
            """检查是否为地理坐标系（经纬度）"""
            if crs is None:
                return False
            return crs.is_geographic
        
        def reproject_to_utm(dem_path):
            """将DEM重新投影到UTM坐标系（如果当前是地理坐标系）"""
            with rasterio.open(dem_path) as src:
                if not is_geographic_crs(src.crs):
                    return dem_path  # 已经是投影坐标系，无需转换
                
                # 确定合适的UTM投影
                bounds = src.bounds
                utm_crs = CRS.from_epsg(32600 + int((bounds.left + bounds.right) / 2 / 6 + 31))
                
                # 创建临时文件路径
                import tempfile
                import os
                temp_dir = tempfile.mkdtemp()
                reprojected_path = os.path.join(temp_dir, "reprojected_dem.tif")
                
                # 执行重投影
                transform, width, height = calculate_default_transform(
                    src.crs, utm_crs, src.width, src.height, *src.bounds)
                
                profile = src.profile.copy()
                profile.update({
                    'crs': utm_crs,
                    'transform': transform,
                    'width': width,
                    'height': height
                })
                
                with rasterio.open(reprojected_path, 'w', **profile) as dst:
                    reproject(
                        source=rasterio.band(src, 1),
                        destination=rasterio.band(dst, 1),
                        src_transform=src.transform,
                        src_crs=src.crs,
                        dst_transform=transform,
                        dst_crs=utm_crs,
                        resampling=Resampling.bilinear)
                
                return reprojected_path
        def calculate_aspect(dem, pixel_size):
            """改进的坡向计算函数，包含边缘处理"""
            # 处理无效值
            dem = np.where(dem == src.nodata, np.nan, dem)
            
            # 计算梯度
            dx = sobel(dem, axis=1, mode='constant', cval=np.nan)
            dy = sobel(dem, axis=0, mode='constant', cval=np.nan)
            
            # 计算坡向（弧度）
            with np.errstate(invalid='ignore'):
                aspect_rad = np.arctan2(-dy, dx)  # 注意符号处理
                aspect_deg = np.degrees(aspect_rad)
                aspect_deg = (aspect_deg + 360) % 360  # 转换为0-360度
            
            # 处理平坦区域
            aspect_deg = np.where(np.isnan(dem), np.nan, aspect_deg)
            return aspect_deg

                # 检查并转换坐标系
        reprojected_path = reproject_to_utm(input_file)
        is_temp_file = reprojected_path != input_file
        
        # 读取DEM数据
        try:
            # 读取DEM数据（可能是原始文件或临时重投影文件）
            with rasterio.open(reprojected_path) as src:
                dem = src.read(1)
                transform = src.transform
                crs = src.crs
                bounds = src.bounds
                nodata = src.nodata
                profile = src.profile.copy()

                # 计算坡向
                aspect = calculate_aspect(dem, pixel_size=transform[0])

                # 增强版栅格输出
                profile.update({
                    'dtype': 'float32',
                    'nodata': np.nan,
                    'count': 1,
                    'compress': 'lzw'
                })

                # 保存坡向结果
                with rasterio.open(output_file, 'w', **profile) as dst:
                    dst.write(aspect.astype(np.float32), 1)
                    dst.update_tags(
                        TIFFTAG_IMAGEDESCRIPTION='Aspect Map',
                        TIFFTAG_SOFTWARE='Python Rasterio'
                    )
                    dst.set_band_description(1, 'Aspect (degrees)')
                
                print(f"坡向计算完成，结果已保存到: {output_file}")
                if is_temp_file:
                    print("注意: 输入DEM已从地理坐标系自动转换为UTM投影坐标系")

        finally:
            # 清理临时文件
            if is_temp_file:
                import os
                os.remove(reprojected_path)
                os.rmdir(os.path.dirname(reprojected_path))
        
        result = output_file
        return ToolResult(output=result)
class TiffyVisualizeTool(BaseTool):
    """对坡度、坡向等进行可视化，生成png格式的图片"""
    
    name: str = "tiff_visualize"
    description: str = "对tiff格式的数据可视化，生成png格式的图片"
    
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "input_file": {
                "type": "string",
                "description": "需要进行可视化的tiff数据"
            },
            "theme": {
                "type": "string",
                "enum": ["slope", "aspect", "Overlay","Reclassification"],
                "description": "被可视化的Tiff数据主题，坡度、坡向、重分类"
            },
            "output_file": {
                "type": "string",
                "description": "自动生成的保存路径，格式为：data/{input_file}_Visualize.png"
            },
            "colormap": {
                "type": "string",
                "enum": ['RdYlBu', 'RdYlGn_r', 'viridis','YlOrBr'],
                "description": "坡度的颜色映射色带"
            },
        },
        "required": ["input_file", "theme",  "output_file"]
    }
    
    async def execute(self, input_file: str, theme: str,  output_file: str,colormap:str='RdYlGn_r') -> ToolResult:
        
        # 读取坡度数据
        with rasterio.open(input_file) as src:
            dataarray = src.read(1)
            nodata = src.nodata  # 获取原始nodata值
    
        # 处理无效值为NaN
        dataarray = np.where(dataarray == nodata, np.nan, dataarray).astype(float)

# 创建地理坐标系可视化
        plt.figure(figsize=(12, 8), facecolor='white')
        if theme == "aspect":
            # 创建掩膜
            mask = np.isnan(dataarray)
            # 自定义HSV颜色映射
            hue = np.zeros_like(dataarray, dtype=float)  # 初始化hue为0
            saturation = np.ones_like(dataarray)
            value = np.ones_like(dataarray)

            # 仅对有效数据计算色相
            valid_mask = ~mask
            hue[valid_mask] = dataarray[valid_mask] / 360.0

            # 将无效区域设置为白色（HSV中S=0，V=1）
            saturation[mask] = 0
            value[mask] = 1

            # 生成RGB图像
            hsv = np.dstack((hue, saturation, value))
            rgb = hsv_to_rgb(hsv)

            # 显示坡向图
            im = plt.imshow(rgb)
            plt.title('Aspect Distribution')
            plt.xlabel('Column')
            plt.ylabel('Row')

            # 创建方向颜色条
            cax = plt.axes([0.92, 0.2, 0.02, 0.6])
            cb = plt.colorbar(im, cax=cax)
            cb.set_ticks([0, 0.25, 0.5, 0.75, 1])
            cb.set_ticklabels(['N(0°)', 'E(90°)', 'S(180°)', 'W(270°)', 'N(360°)'])
            cb.set_label('Aspect Direction')
        elif theme == "slope":
            # 自定义颜色映射（从绿色到红色）
            cmap = plt.get_cmap(colormap)  # 反转的RdYlGn色带：绿色(低) -> 黄色 -> 红色(高)
            norm = Normalize(vmin=0, vmax=45)  # 假设坡度范围0-45度

            # 显示坡度图
            im = plt.imshow(dataarray, cmap=cmap, norm=norm)
            plt.title('Slope Distribution')
            plt.xlabel('Column')
            plt.ylabel('Row')

            # 创建专业颜色条
            cax = plt.axes([0.92, 0.2, 0.02, 0.6])
            cb = plt.colorbar(im, cax=cax)
            cb.set_label('Slope (degrees)', rotation=270, labelpad=25)

            # 设置智能刻度
            tick_values = [0, 5, 15, 25, 35, 45]
            cb.set_ticks(tick_values)
            cb.set_ticklabels([f'{v}°' for v in tick_values])

            # 添加等高线（可选）
            # CS = plt.contour( dataarray, levels=[5, 15, 30], colors='black', linewidths=0.5)
            # plt.clabel(CS, inline=True, fontsize=8)
        elif theme == "Overlay":
            # 选择颜色变化明显的色带
            overlay_cmap = plt.get_cmap('YlOrBr')
            # 计算有效数据范围
            valid_data = dataarray[~np.isnan(dataarray)]
            vmin = np.nanmin(valid_data)
            vmax = np.nanmax(valid_data)
            # 自动分级ticks（10个）
            ticks = np.linspace(vmin, vmax, 10)
            # 显示叠置图
            im = plt.imshow(dataarray, cmap=overlay_cmap, vmin=vmin, vmax=vmax)
            plt.title('Overlay Distribution')
            plt.xlabel('Column')
            plt.ylabel('Row')
            # 创建连续色带图例
            cax = plt.axes([0.92, 0.2, 0.02, 0.6])
            cb = plt.colorbar(im, cax=cax, ticks=ticks)
            cb.set_label('Overlay Value', rotation=270, labelpad=25)
            cb.ax.set_yticklabels([f'{tick:.2f}' for tick in ticks])    
        elif theme == "Reclassification":
            # 自定义颜色映射（从绿色到红色）
            cmap = plt.get_cmap(colormap)
            # 获取唯一分类号（已分好等级）
            valid_data = dataarray[~np.isnan(dataarray)]
            unique_classes = np.unique(valid_data)
            # 只保留整数型分类号
            unique_classes = np.sort(np.unique(unique_classes.astype(int)))
            # 显示重分类图
            im = plt.imshow(dataarray, cmap=cmap, vmin=unique_classes[0], vmax=unique_classes[-1])
            plt.title('Reclassification Distribution')
            plt.xlabel('Column')
            plt.ylabel('Row')
            # 创建色带图例，ticks严格对应唯一分类号
            cax = plt.axes([0.92, 0.2, 0.02, 0.6])
            cb = plt.colorbar(im, cax=cax, ticks=unique_classes)
            cb.set_label('Class', rotation=270, labelpad=25)
            cb.ax.set_yticklabels([str(cls) for cls in unique_classes])



        plt.savefig(output_file, 
           dpi=300, 
           bbox_inches='tight',
           facecolor='white',
           edgecolor='white',
           transparent=False)

        plt.show()
        result =output_file
            
        return ToolResult(output=result)
class TiffOverlayTool(BaseTool):
    """对栅格数据、tiff数据等进行叠置分析"""
    
    name: str = "tiff_overlay"
    description: str = "对两个栅格数据进行叠置分析"
    
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "input_raster1": {
                "type": "string",
                "description": "输入的栅格数据1"
            },
            "input_raster2": {
                "type": "string",
                "description": "输入的栅格数据2"
            },
            "output_file": {
                "type": "string",
                "description": "自动生成的保存路径，格式为：data/{栅格1}_Overlay_{栅格2}.tif"
            },
             "expression": {
                "type": "string",
                "description": "输入的叠置表达式"
            },
             "force": {
                "type": "boolean",
                "description": "是否强制执行计算，即使形状或投影不一致"
            },
        },
        "required": ["input_file1", "input_file2",  "output_file"]
    }
    
    async def execute(self, input_raster1: str, input_raster2: str,  output_file: str,expression:str,force:bool = True) -> ToolResult:
        
       with rasterio.open(input_raster1) as src1, rasterio.open(input_raster2) as src2:
        # 检查形状和投影是否一致
        if not force:
            assert src1.shape == src2.shape, "两个栅格的形状不一致，请检查输入数据。"
            assert src1.crs == src2.crs, "两个栅格的投影不一致，请检查输入数据。"
        
        # 读取数据
        band1 = src1.read(1)
        band2 = src2.read(1)
        
        # 如果形状不一致且强制执行，则裁剪或填充数据
        if force and src1.shape != src2.shape:
            # 这里简单地裁剪到较小的形状，实际应用中可能需要更复杂的处理
            min_height = min(band1.shape[0], band2.shape[0])
            min_width = min(band1.shape[1], band2.shape[1])
            band1 = band1[:min_height, :min_width]
            band2 = band2[:min_height, :min_width]
        
        # 执行计算
        # 使用eval函数执行表达式，a代表第一个栅格，b代表第二个栅格
        result = eval(expression, {'a': band1, 'b': band2, 'np': np})
        
        # 写入输出文件
        profile = src1.profile
        with rasterio.open(output_file, 'w', **profile) as dst:
            dst.write(result, 1)
            
            result = output_file
        return ToolResult(output=result)     
class DistanceAnalysis(BaseTool):
    """对输入的POI数据进行距离分析"""
    
    name: str = "distance_analysis"
    description: str = "对输入的POI数据进行距离分析,输出为栅格数据（tif格式）"
    
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "input_file": {
                "type": "string",
                "description": "输入的Shapefile数据文件路径"
            },
            "output_file": {
                "type": "string",
                "description": "输出的距离分析结果数据，格式为：data/{input_file}_distance.tif"
            },
            "resolution": {
                "type": "number",
                "description": "输出栅格的分辨率(米)"
            },
            "buffer": {
                "type": "number",
                "description": "在POI范围外添加的缓冲区距离(米)"
            },
            "boundary_file": {
                "type": "number",
                "description": "边界shp文件路径"
            },

        },
        "required": ["input_file", "output_file","boundary_file"]
    }
    
    async def execute(self, input_file:str, output_file:str, boundary_file,resolution=100, buffer=1000, ) -> ToolResult:
        # 1. 读取POI数据并确保使用投影坐标系
        try:
            gdf = gpd.read_file(input_file)
            print(f"原始坐标系: {gdf.crs}")
            
            # 如果不在投影坐标系中，转换为UTM
            if not gdf.crs.is_projected:
                utm_crs = CRS.from_user_input(gdf.estimate_utm_crs())
                gdf = gdf.to_crs(utm_crs)
                print(f"已转换为投影坐标系: {gdf.crs}")
                
            print(f"成功读取 {len(gdf)} 个POI点")
        except Exception as e:
            print(f"读取POI数据失败: {e}")
            return
        
        # 2. 确定研究区域范围
        if boundary_file:
            # 读取边界文件并确保坐标系一致
            try:
                boundary = gpd.read_file(boundary_file).to_crs(gdf.crs)
                bounds = boundary.total_bounds
                print("使用指定边界范围")
            except Exception as e:
                print(f"读取边界文件失败，将使用POI范围: {e}")
                bounds = gdf.total_bounds
        else:
            bounds = gdf.total_bounds
        
        minx, miny, maxx, maxy = bounds
        
        # 添加缓冲区
        minx -= buffer
        miny -= buffer
        maxx += buffer
        maxy += buffer
        
        # 计算网格行列数
        x_size = int((maxx - minx) / resolution) + 1
        y_size = int((maxy - miny) / resolution) + 1
        
        # 创建网格点坐标
        x_coords = np.linspace(minx, maxx, x_size)
        y_coords = np.linspace(maxy, miny, y_size)  # 从maxy到miny
        xx, yy = np.meshgrid(x_coords, y_coords)
        grid_points = np.column_stack([xx.ravel(), yy.ravel()])
        
        # 3. 提取POI点坐标
        poi_coords = np.array([(geom.x, geom.y) for geom in gdf.geometry])
        
        # 4. 计算欧式距离
        print("正在计算欧式距离...")
        distances = cdist(grid_points, poi_coords, 'euclidean')
        min_distances = np.min(distances, axis=1)
        distance_grid = min_distances.reshape(y_size, x_size)
        
        # 检查数据范围
        print(f"距离值范围: {np.min(distance_grid):.2f} 到 {np.max(distance_grid):.2f} 米")
        
        # 5. 创建并保存GeoTIFF
        print("正在生成GeoTIFF...")
        
        # 创建转换矩阵
        transform = from_origin(minx, maxy, resolution, resolution)
        
        # 设置输出参数
        profile = {
            'driver': 'GTiff',
            'height': y_size,
            'width': x_size,
            'count': 1,
            'dtype': np.float32,
            'crs': gdf.crs,
            'transform': transform,
            'compress': 'lzw',
            'nodata': -9999
        }
        
        # 先保存完整范围的栅格
        temp_tiff = output_file.replace('.tif', '_temp.tif')
        with rasterio.open(temp_tiff, 'w', **profile) as dst:
            dst.write(distance_grid.astype(np.float32), 1)
        
        # 如果有边界文件，进行裁剪
        if boundary_file:
            print("正在根据边界裁剪栅格...")
            try:
                # 读取临时栅格
                with rasterio.open(temp_tiff) as src:
                    # 执行裁剪
                    out_image, out_transform = mask(src, boundary.geometry, crop=True)
                    out_meta = src.meta.copy()
                    
                    # 更新元数据
                    out_meta.update({
                        "driver": "GTiff",
                        "height": out_image.shape[1],
                        "width": out_image.shape[2],
                        "transform": out_transform,
                        "compress": "lzw"
                    })
                    
                    # 保存裁剪后的结果
                    with rasterio.open(output_file, 'w', **out_meta) as dest:
                        dest.write(out_image)
                    
                    print("裁剪完成")
            except Exception as e:
                print(f"裁剪失败: {e}, 将保存未裁剪结果")
                import shutil
                shutil.copy(temp_tiff, output_file)
        else:
            import shutil
            shutil.copy(temp_tiff, output_file)
        
        # 删除临时文件
        import os
        os.remove(temp_tiff)
        
        print(f"GeoTIFF已保存至: {output_file}")

        return ToolResult(output=output_file)
class Reclassification(BaseTool):
    """对输入的tiff数据进行重分类"""
    
    name: str = "reclassification"
    description: str = "对输入的tiff栅格数据进行重分类,输出为栅格数据（tif格式）"
    
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "input_path": {
                "type": "string",
                "description": "输入的栅格数据文件路径"
            },
            "output_path": {
                "type": "string",
                "description": "输出的重分类结果数据，格式为：data/{input_file}_reclass.tif"
            },
            "num_classes": {
                "type": "number",
                "description": "重分类的数量，按照等间距分类法进行分类"
            },
            "boundary_shp": {
                "type": "string",
                "description": "边界shp文件路径"
            },
            "reverse": {
                "type": "boolean",
                "description": "是否对重分类结果取反（即高值变低值，低值变高值)true表示需要取反m",
                "default": True
            }
        },
        "required": ["input_path", "output_path","boundary_shp"]
    }
    
    async def execute(self, input_path, output_path, boundary_shp, num_classes: int = 10, reverse: bool = False) -> ToolResult:
        # 参数检查
        if not boundary_shp or not os.path.exists(boundary_shp):
            raise ValueError("必须提供有效的边界SHP文件路径")

        # 读取边界数据
        gdf = gpd.read_file(boundary_shp)
        
        with rasterio.open(input_path) as src:
            # 坐标系对齐
            gdf = gdf.to_crs(src.crs)
            shapes = [mapping(geom) for geom in gdf.geometry]
            
            # 自动确定nodata值
            src_nodata = src.nodata
            if src_nodata is None:
                # 根据数据类型自动生成nodata值
                dtype = src.dtypes[0]
                if np.issubdtype(dtype, np.integer):
                    src_nodata = np.iinfo(dtype).min
                else:
                    src_nodata = -9999

            # 执行裁剪（关键修改）
            try:
                out_image, out_transform = mask(
                    src, 
                    shapes,
                    crop=True,
                    all_touched=True,
                    filled=True,  # 填充边界外区域为nodata
                    nodata=src_nodata
                )
            except ValueError as e:
                raise RuntimeError(f"裁剪失败: {str(e)} (请检查边界和栅格是否有重叠)")

            # 获取数据并创建有效掩码
            data = out_image[0]
            valid_mask = (data != src_nodata)
            
            # 检查有效数据存在性
            if not np.any(valid_mask):
                raise ValueError("裁剪后无有效数据，请检查输入数据的覆盖范围")

            # 计算分类边界（仅使用有效数据）
            valid_data = data[valid_mask]
            min_val, max_val = np.min(valid_data), np.max(valid_data)
            # 始终用升序bins
            bins = np.linspace(min_val, max_val, num_classes + 1)
            reclassified = np.digitize(data, bins) - 1
            if reverse:
                reclassified = (num_classes - 1) - reclassified
            # 设置输出nodata值（选择最大分类号+1，未分类像元）
            output_nodata = num_classes
            reclassified = np.where(valid_mask, reclassified, output_nodata)
            # 保证所有分类号在0~num_classes-1之间
            reclassified = np.clip(reclassified, 0, num_classes-1, out=reclassified, where=(reclassified!=output_nodata))

            # 更新元数据
            profile = src.profile.copy()
            profile.update({
                "driver": "GTiff",
                "height": reclassified.shape[0],
                "width": reclassified.shape[1],
                "transform": out_transform,
                "dtype": "uint8",
                "nodata": output_nodata,
                "count": 1
            })
            # 写入文件
            with rasterio.open(output_path, 'w', **profile) as dst:
                dst.write(reclassified.astype(np.uint8), 1)

        return ToolResult(output=output_path)
class WeightedOverlay(BaseTool):
    """输入多个重分类后的TIFF数据进行加权叠加"""
    
    name: str = "weightedoverlay"
    description: str = "输入多个重分类后的TIFF数据进行加权叠加"
    
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "input_rasters": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "输入的栅格数据文件路径"},
                        "weight": {"type": "number", "description": "该栅格的权重"}
                    },
                    "required": ["path", "weight"]
                },
                "description": "输入的tiff路径和权重组成的列表，如: [{\"path\": \"a.tif\", \"weight\": 0.5}, {\"path\": \"b.tif\", \"weight\": 0.5}]"
            },
            "output_path": {
                "type": "string",
                "description": "输出的加权叠加结果tiff路径"
            }
        },
        "required": ["input_rasters", "output_path"]
    }
    
    async def execute(self, input_rasters, output_path) -> ToolResult:
        import numpy as np
        import rasterio
        from rasterio.warp import reproject, Resampling

        # 参数有效性检查
        if not input_rasters or len(input_rasters) < 1:
            raise ValueError("input_rasters 至少需要一个元素")
        if any('path' not in r or 'weight' not in r for r in input_rasters):
            raise ValueError("input_rasters 每个元素都需包含 path 和 weight")

        # 读取基准栅格
        with rasterio.open(input_rasters[0]['path']) as base_src:
            base_profile = base_src.profile.copy()
            base_crs = base_src.crs
            base_transform = base_src.transform
            base_shape = base_src.shape
            base_data = base_src.read(1)
            base_nodata = base_src.nodata
            valid_mask = (base_data != base_nodata) if base_nodata is not None else np.ones_like(base_data, dtype=bool)
            result = np.where(valid_mask, base_data * input_rasters[0]['weight'], 0).astype(np.float32)

            # 处理其他栅格
            for raster_info in input_rasters[1:]:
                raster_path = raster_info['path']
                weight = raster_info['weight']
                with rasterio.open(raster_path) as src:
                    # 坐标系检查
                    if src.crs != base_crs:
                        raise ValueError(f"栅格 {raster_path} 坐标系与基准栅格不一致")
                    data = src.read(1)
                    src_nodata = src.nodata
                    current_valid = (data != src_nodata) if src_nodata is not None else np.ones_like(data, dtype=bool)
                    # 分辨率或地理变换不一致时重采样
                    if src.shape != base_shape or src.transform != base_transform:
                        resampled_data = np.empty(base_shape, dtype=np.float32)
                        resampled_valid = np.empty(base_shape, dtype=np.float32)
                        reproject(
                            source=rasterio.band(src, 1),
                            destination=resampled_data,
                            src_transform=src.transform,
                            src_crs=src.crs,
                            dst_transform=base_transform,
                            dst_crs=base_crs,
                            resampling=Resampling.bilinear
                        )
                        reproject(
                            source=current_valid.astype(np.float32),
                            destination=resampled_valid,
                            src_transform=src.transform,
                            src_crs=src.crs,
                            dst_transform=base_transform,
                            dst_crs=base_crs,
                            resampling=Resampling.nearest
                        )
                        data = resampled_data
                        current_valid = resampled_valid > 0.5
                    weighted_data = np.where(current_valid, data * weight, 0)
                    result += weighted_data.astype(np.float32)
                    valid_mask |= current_valid

        # 设置NoData：仅在所有输入无效时设为NoData
        nodata_value = base_profile.get('nodata', -9999)
        result = np.where(valid_mask, result, nodata_value)
        base_profile.update(
            dtype=rasterio.float32,
            count=1,
            compress='lzw',
            nodata=nodata_value
        )
        with rasterio.open(output_path, 'w', **base_profile) as dst:
            dst.write(result, 1)
        return ToolResult(output=output_path)  
class Clip(BaseTool):
    """输入矢量边界裁剪栅格数据"""
    
    name: str = "clip"
    description: str = "输入矢量边界裁剪栅格数据"
    
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "input_raster": {
                "type": "string",
                "description": "输入的栅格数据文件路径"
            },
            "output_raster": {
                "type": "string",
                "description": "输出的裁剪后的栅格数据，后缀为.tif"
            },
            "shp_path": {
                "type": "string",
                "description": "用于裁剪的边界shp文件路径"
            },

        },
        "required": ["input_raster", "output_raster","shp_path"]
    }
    
    async def execute(self, input_raster, output_raster, shp_path, nodata=None) -> ToolResult:
        # 读取矢量边界文件
        shp = gpd.read_file(shp_path)
        
        # 打开栅格文件
        with rasterio.open(input_raster) as src:
            # 转换矢量坐标系到栅格坐标系
            shp = shp.to_crs(src.crs)
            geometries = shp.geometry.tolist()

            # 自动确定nodata值（优先使用输入的nodata参数）
            target_nodata = nodata if nodata is not None else src.nodata
            if target_nodata is None:
                # 当所有数值均为有效值时，使用一个极值作为nodata
                target_nodata = src.dtypes[0].min if 'int' in src.dtypes[0].name else -9999

            # 执行裁剪操作
            out_image, out_transform = mask(
                src,
                geometries,
                crop=True,
                nodata=target_nodata
            )

            # 更新输出元数据
            out_meta = src.meta.copy()
            out_meta.update({
                "driver": "GTiff",
                "height": out_image.shape[1],
                "width": out_image.shape[2],
                "transform": out_transform,
                "nodata": target_nodata
            })

            # 写入输出文件
            with rasterio.open(output_raster, "w", **out_meta) as dest:
                dest.write(out_image)


        return ToolResult(output=output_raster)