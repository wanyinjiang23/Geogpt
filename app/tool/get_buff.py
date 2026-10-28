import geopandas as gpd
from typing import Any
from shapely.geometry import Point,MultiPolygon
from shapely.ops import unary_union
from pathlib import Path
from pyproj import CRS
import pandas as pd 
import re

"""
这里注释一下，buffer_analysis函数中首先将输入的点文件从地理坐标系转换为了投影坐标，并且实现的消除内容的边界
对于缓冲区的叠加、相交、擦除操作使用的是这个函数
chang_utm是用来将地理坐标转换为投影坐标用的
compute_buffer_intersection先检查输入的shp是不是投影坐标 否则用chang_utm来转换
这里代码有点写重复了

creatbuffer是只有缓冲区查询的地方才用到，中间直接传递shp，也没有将生成的缓冲区保存
"""
def buffer_analysis(gdf:gpd.GeoDataFrame, buffer_distance: float, output_path: str) -> str:
    """
    对输入的矢量数据进行缓冲区分析，并保存结果。
    参数:
        shp: 输入的shp对象。
        buffer_distance (float): 缓冲距离（单位：米）。
        output_path (str): 缓冲区分析结果的保存路径。
    """
   
    print("数据加载成功！共有{}条记录。".format(len(gdf)))

     #检查数据的坐标系
    if gdf.crs is None:
        print("警告：数据没有定义坐标系，假设为 WGS84 (EPSG:4326)。")
        gdf.set_crs(epsg=4326, inplace=True)
    elif gdf.crs != "EPSG:4326":
        print("警告：数据不是 WGS84 坐标系，正在转换为 WGS84。")
        gdf.to_crs(epsg=4326, inplace=True)

    # 3. 计算数据的几何中心点
    centroid = gdf.geometry.centroid
    avg_lon = centroid.x.mean()
    avg_lat = centroid.y.mean()
    centroid_point = Point(avg_lon, avg_lat)  # 创建一个新的点几何

    # 4. 根据中心点计算合适的 UTM 投影 EPSG 代码
    def calculate_utm_epsg(lon, lat):
        """根据经纬度计算合适的 UTM 投影 EPSG 代码"""
        utm_zone = int((lon + 180) // 6 + 1)
        if lat >= 0:
            return 32600 + utm_zone  # 北半球
        else:
            return 32700 + utm_zone  # 南半球

    lon, lat = centroid_point.x, centroid_point.y
    utm_epsg = calculate_utm_epsg(lon, lat)
    print("检测到合适的 UTM 投影 EPSG 代码为：{}".format(utm_epsg))

    # 5. 将数据转换为 UTM 投影
    gdf_utm = gdf.to_crs(epsg=utm_epsg)
    print("数据已转换为 UTM 投影坐标系 (EPSG:{}).".format(utm_epsg))
        
    # 创建缓冲区
    buffer_gdf = gdf_utm.copy()
    buffer_gdf['geometry'] = buffer_gdf.geometry.buffer(buffer_distance)
    
    # 转换回WGS84坐标系
    #buffer_gdf = buffer_gdf.to_crs(epsg=4326)

    #消除内部边界
    smoothed_geom = unary_union(buffer_gdf.geometry)
    buffer_gdf = gpd.GeoDataFrame(geometry=[smoothed_geom], crs=buffer_gdf.crs)
    # 保存结果
    buffer_gdf.to_file(output_path, encoding='utf-8')
    print(f"缓冲区分析完成，结果已保存至：{output_path}")
    
    return output_path
def chang_utm(gdf: gpd.GeoDataFrame):
    current_crs = gdf.crs

    # 如果当前没有坐标系，直接返回
    if current_crs is None:
        print("警告：输入的要素类对象没有定义坐标系。")
        return gdf

    # 使用 pyproj 检查是否为地理坐标系
    if CRS(current_crs).is_geographic:
        print("检测到地理坐标系，正在转换为投影坐标系...")
        centroid = gdf.geometry.centroid
        avg_lon = centroid.x.mean()
        avg_lat = centroid.y.mean()
        centroid_point = Point(avg_lon, avg_lat)  # 创建一个新的点几何
        def calculate_utm_epsg(lon, lat):
            """根据经纬度计算合适的 UTM 投影 EPSG 代码"""
            utm_zone = int((lon + 180) // 6 + 1)
            if lat >= 0:
                return 32600 + utm_zone  # 北半球
            else:
                return 32700 + utm_zone  # 南半球

        lon, lat = centroid_point.x, centroid_point.y
        utm_epsg = calculate_utm_epsg(lon, lat)
        print("检测到合适的 UTM 投影 EPSG 代码为：{}".format(utm_epsg))
        # 5. 将数据转换为 UTM 投影
        gdf_utm = gdf.to_crs(epsg=utm_epsg)
        print("数据已转换为 UTM 投影坐标系 (EPSG:{}).".format(utm_epsg))
        return gdf_utm
    else:
        print("输入的要素类对象已经是投影坐标系，无需转换。")
        return gdf  
def compute_buffer_intersection(input_shp1, input_shp2, output_intersect_shp:str=r"C:\Users\ASUS\Desktop\data\intersect.shp"):
    """
    对输入的两个面要素文件进行叠加分析，输出相交区域的面要素。

    参数：
    input_shp1 (str): 第一个输入的面要素shp文件路径。
    input_shp2 (str): 第二个输入的面要素shp文件路径。
    output_intersect_shp (str): 输出的相交面要素shp文件路径。

    返回：
    GeoDataFrame: 包含相交区域的GeoDataFrame。
    """
    # 读取输入的两个面要素文件
    gdf1 = chang_utm(gpd.read_file(input_shp1))
    gdf2 = chang_utm(gpd.read_file(input_shp2))

    if len(gdf1) == 0 or len(gdf2) == 0:
        raise ValueError("输入的Shapefile文件没有面要素。")
    
    
    
    # 确保几何有效性（修复可能的无效几何）
    gdf1.geometry = gdf1.geometry.buffer(0)
    gdf2.geometry = gdf2.geometry.buffer(0)
    
    intersections = []  # 存储所有相交区域
    
    # 遍历两个GeoDataFrame中的所有面要素组合
    for idx1, row1 in gdf1.iterrows():
        for idx2, row2 in gdf2.iterrows():
            geom1 = row1.geometry
            geom2 = row2.geometry
            
            if geom1.intersects(geom2):
                inter = geom1.intersection(geom2)
                if not inter.is_empty:
                    # 处理MultiPolygon，分解为单个Polygon
                    if isinstance(inter, MultiPolygon):
                        for poly in inter.geoms:
                            intersections.append(poly)
                    else:
                        intersections.append(inter)
    
    # 创建结果GeoDataFrame
    if intersections:
        result_gdf = gpd.GeoDataFrame(geometry=intersections, crs=gdf1.crs)
        smoothed_geom = unary_union(result_gdf.geometry)
        result_gdf = gpd.GeoDataFrame(geometry=[smoothed_geom], crs=result_gdf.crs)
    else:
        print("警告：未找到任何相交区域。")
        result_gdf = gpd.GeoDataFrame(geometry=[], crs=gdf1.crs)
    
    # 转换回WGS84坐标系
    #result_gdf = result_gdf.to_crs(epsg=4326)
    
    # 输出到shp文件
    result_gdf.to_file(output_intersect_shp)
    print("相交区域已成功保存到：", output_intersect_shp)
    return output_intersect_shp
def creat_buff(shp, buffer_distance: int = 500 ):
    shp_utm = chang_utm(shp)
    # 创建缓冲区
    buffer_gdf = shp_utm.copy()

    buffer_gdf['geometry'] = buffer_gdf.geometry.buffer(buffer_distance)
        
    # 转换回WGS84坐标系
    #buffer_gdf = buffer_gdf.to_crs(epsg=4326)
        
    # 保存结果
    #buffer_gdf.to_file(output_path, encoding='utf-8')
    print(f"缓冲区分析完成")
        
    return buffer_gdf
def query_point_by_name(point_name, inputfile, name_field='名称'):
    """
    从多个shp文件中查询符合要求名称的点
    
    参数:
        point_name: 要查询的点名称
        inputfile: shp文件路径
        name_field: 名称字段名(默认为'名称')
    
    返回:
        包含所有匹配点的GeoDataFrame
    """
    # 预处理输入的名称：去除括号及其内容
    clean_input_name = re.sub(r'\(.*?\)', '', point_name).strip()
    matched_points = []
    try:
        gdf = gpd.read_file(inputfile)
        # 检查是否存在名称字段
        if name_field in gdf.columns:
            # 预处理数据中的名称：去除括号及其内容
            gdf['clean_name'] = gdf[name_field].apply(
                lambda x: re.sub(r'\(.*?\)', '', str(x)).strip()
            )
            # 查找名称匹配的点
            matches = gdf[gdf['clean_name'] == clean_input_name]
            if not matches.empty:
                matched_points.append(matches.drop(columns=['clean_name']))
                print(f"在文件 {inputfile} 中找到 {len(matches)} 个匹配点")
    except Exception as e:
        print(f"读取文件 {inputfile} 时出错: {e}")
    
    if not matched_points:
        print(f"在所有文件中未找到名称为'{point_name}'的点要素")
        return None
    
    result = gpd.GeoDataFrame(pd.concat(matched_points, ignore_index=True))
    
    # 确保所有结果使用相同的CRS(以第一个匹配结果的CRS为准)
    if len(result) > 0:
        target_crs = result.crs
        for i, gdf in enumerate(matched_points):
            if gdf.crs != target_crs:
                matched_points[i] = gdf.to_crs(target_crs)
        result = gpd.GeoDataFrame(pd.concat(matched_points, ignore_index=True))
    
    print(f"共找到 {len(result)} 个名称为'{point_name}'的点要素")
    return result
def query_intersection(shp_point, shp_buffer,output_path):
   # 确保坐标系一致
    if shp_point.crs != shp_buffer.crs:
        print("警告：坐标系不一致，正在统一坐标系")
        shp_buffer = shp_buffer.to_crs(shp_point.crs)
    shp_buffer_renamed = shp_buffer.rename(columns={col: f"buff_{col}" for col in shp_buffer.columns if col != 'geometry'})
   # 空间连接：查找点是否位于缓冲区内
    query_point = gpd.sjoin(shp_point, shp_buffer_renamed, how="inner", predicate="within")
    # 去重：每个点只保留第一次匹配
    query_point = query_point.drop_duplicates(subset="名称", keep="first")

    print(query_point[['名称', '地址','电话']])

    if not query_point.empty:
        # 只保留原始点要素的字段（排除所有 buff_ 开头的字段）
        cols_to_keep = [col for col in query_point.columns if not col.startswith('buff_')]
        query_point = query_point[cols_to_keep]

        # 确保几何列存在
        query_point = gpd.GeoDataFrame(query_point, geometry="geometry", crs=shp_point.crs)
        query_point.to_file(output_path, encoding="utf-8")  
        print(f"共有 {len(query_point)} 个要素符合要求")
        print(f"结果已保存至：{output_path}")
    else:
        print("没有查询到结果，未生成文件")

    return output_path if not query_point.empty else None
def compute_buffer_union(input_shp1, input_shp2, output_union_shp:str=r"C:\Users\ASUS\Desktop\data\union.shp"):

    """
    计算两个面要素的并集（Union），合并为一个面要素文件。

    参数：
    input_shp1 (str): 第一个输入的面要素shp文件路径。
    input_shp2 (str): 第二个输入的面要素shp文件路径。
    output_union_shp (str): 输出并集结果的shp文件路径。

    返回：
    GeoDataFrame: 包含相交区域的GeoDataFrame。
    """
    # 读取输入的两个面要素文件
    gdf1 = chang_utm(gpd.read_file(input_shp1))
    gdf2 = chang_utm(gpd.read_file(input_shp2))
    if len(gdf1) == 0 or len(gdf2) == 0:
        raise ValueError("输入的Shapefile文件没有面要素。")
    # 确保几何有效性（修复可能的无效几何）
    gdf1.geometry = gdf1.geometry.buffer(0)
    gdf2.geometry = gdf2.geometry.buffer(0)
    
    union_gdf = gpd.overlay(gdf1, gdf2, how="union")
    
    
    # 转换回WGS84坐标系
    #result_gdf = result_gdf.to_crs(epsg=4326)
    
    #消除内部边界
    smoothed_geom = unary_union(union_gdf.geometry)
    smoothed_gdf = gpd.GeoDataFrame(geometry=[smoothed_geom], crs=union_gdf.crs)
    # 输出到shp文件
    smoothed_gdf.to_file(output_union_shp)
    print("相交区域已成功保存到：", output_union_shp)
    return output_union_shp
def compute_buffer_difference(input_shp1, input_shp2, output_diff_shp: str = r"C:\Users\ASUS\Desktop\data\difference.shp"):
    """
    计算两个面要素的差集（Difference），即从第一个面要素中擦除与第二个面要素重叠的部分。

    参数：
    input_shp1 (str|GeoDataFrame): 主面要素shp文件路径或GeoDataFrame（保留的目标）。
    input_shp2 (str|GeoDataFrame): 擦除面要素shp文件路径或GeoDataFrame（用于擦除的部分）。
    output_diff_shp (str): 输出差集结果的shp文件路径。

    返回：
    str: 输出文件路径。
    """
    # 读取输入数据（支持直接传入GeoDataFrame）
    gdf1 = chang_utm(input_shp1 if isinstance(input_shp1, gpd.GeoDataFrame) else gpd.read_file(input_shp1))
    gdf2 = chang_utm(input_shp2 if isinstance(input_shp2, gpd.GeoDataFrame) else gpd.read_file(input_shp2))
    
    if len(gdf1) == 0 or len(gdf2) == 0:
        raise ValueError("输入的要素没有面要素。")
    
    # 确保几何有效性
    gdf1.geometry = gdf1.geometry.buffer(0)
    gdf2.geometry = gdf2.geometry.buffer(0)
    
    # 计算差集（逐个几何处理）
    diff_geoms = []
    for geom1 in gdf1.geometry:
        # 对每个主几何执行擦除操作
        diff_geom = geom1.difference(unary_union(gdf2.geometry))
        if not diff_geom.is_empty:  # 这里检查单个几何是否为空
            if diff_geom.geom_type == "MultiPolygon":
                diff_geoms.extend(list(diff_geom.geoms))
            else:
                diff_geoms.append(diff_geom)
    
    # 创建结果GeoDataFrame
    if not diff_geoms:
        print("警告：擦除后结果为空。")
        diff_gdf = gpd.GeoDataFrame(geometry=[], crs=gdf1.crs)
    else:
        diff_gdf = gpd.GeoDataFrame(geometry=diff_geoms, crs=gdf1.crs)
        # 消除内部边界
        smoothed_geom = unary_union(diff_gdf.geometry)
        diff_gdf = gpd.GeoDataFrame(geometry=[smoothed_geom], crs=gdf1.crs)
    
    # 保存结果
    diff_gdf.to_file(output_diff_shp)
    print(f"擦除结果已保存到：{output_diff_shp}")
    return output_diff_shp
# 示例调用

if __name__ == "__main__":
      a = 1 