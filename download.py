import os
import json
import requests
import re
from urllib.parse import urljoin, urlparse
import time
import logging
from concurrent.futures import ThreadPoolExecutor
import argparse
from PIL import Image  # 添加PIL库用于图像处理

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("download.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# 全局变量
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "live2dMaster.json")
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
MAX_WORKERS = 5  # 并发下载线程数
DOWNLOADED_FILES = set()  # 已下载文件缓存，避免重复下载

def ensure_dir(directory):
    """确保目录存在，如果不存在则创建"""
    if not os.path.exists(directory):
        os.makedirs(directory)
        logging.info(f"创建目录: {directory}")

def download_file(url, save_path):
    """下载文件到指定路径"""
    # 如果文件已下载，跳过
    if url in DOWNLOADED_FILES:
        logging.info(f"文件已存在，跳过: {url}")
        return
    
    # 确保目录存在
    ensure_dir(os.path.dirname(save_path))
    
    try:
        # 添加重试机制
        for retry in range(3):
            try:
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                
                with open(save_path, 'wb') as f:
                    f.write(response.content)
                
                DOWNLOADED_FILES.add(url)
                logging.info(f"下载成功: {url} -> {save_path}")
                break
            except requests.exceptions.RequestException as e:
                logging.warning(f"下载失败(尝试 {retry+1}/3): {url}, 错误: {e}")
                if retry == 2:  # 最后一次重试
                    raise
                time.sleep(2)  # 等待一段时间再重试
                
    except Exception as e:
        logging.error(f"下载失败: {url}, 错误: {e}")
        raise

def convert_webp_to_png(webp_path):
    """将webp格式图片转换为png格式"""
    try:
        # 检查文件是否是webp格式
        if not webp_path.lower().endswith('.webp'):
            return webp_path  # 不是webp文件，直接返回原路径
        
        # 构建png输出路径
        png_path = os.path.splitext(webp_path)[0] + '.png'
        
        # 转换图片
        img = Image.open(webp_path)
        img.save(png_path, 'PNG')
        
        logging.info(f"图片转换成功: {webp_path} -> {png_path}")
        
        # 删除原webp文件
        os.remove(webp_path)
        
        return png_path
    except Exception as e:
        logging.error(f"图片转换失败: {webp_path}, 错误: {e}")
        return webp_path  # 失败时返回原路径

def parse_model_json(json_url, model_dir):
    """解析模型JSON文件，获取所有需要下载的资源"""
    # 下载模型JSON文件
    json_file_path = os.path.join(model_dir, os.path.basename(json_url))
    download_file(json_url, json_file_path)
    
    # 创建资源子目录
    textures_dir = os.path.join(model_dir, "textures")
    motions_dir = os.path.join(model_dir, "motions")
    expressions_dir = os.path.join(model_dir, "expressions")
    ensure_dir(textures_dir)
    ensure_dir(motions_dir)
    ensure_dir(expressions_dir)
    
    # 解析JSON文件
    with open(json_file_path, 'r', encoding='utf-8') as f:
        model_data = json.load(f)
    
    # 提取所有资源URL和对应的本地保存路径
    base_url = os.path.dirname(json_url) + '/'
    resources_to_download = []
    
    # 获取文件夹和模型文件
    if "FileReferences" in model_data:
        refs = model_data["FileReferences"]
        
        # 模型文件
        if "Moc" in refs:
            moc_url = urljoin(base_url, refs["Moc"])
            moc_path = os.path.join(model_dir, os.path.basename(refs["Moc"]))
            resources_to_download.append((moc_url, moc_path))
        
        # 纹理文件
        if "Textures" in refs:
            for texture in refs["Textures"]:
                texture_url = urljoin(base_url, texture)
                texture_path = os.path.join(textures_dir, os.path.basename(texture))
                resources_to_download.append((texture_url, texture_path))
        
        # 物理文件
        if "Physics" in refs:
            physics_url = urljoin(base_url, refs["Physics"])
            physics_path = os.path.join(model_dir, os.path.basename(refs["Physics"]))
            resources_to_download.append((physics_url, physics_path))
        
        # 动作文件
        if "Motions" in refs:
            for motion_group_name, motion_group in refs["Motions"].items():
                # 为每个动作组创建子目录
                motion_group_dir = os.path.join(motions_dir, motion_group_name)
                ensure_dir(motion_group_dir)
                
                for motion in motion_group:
                    motion_url = urljoin(base_url, motion["File"])
                    motion_path = os.path.join(motion_group_dir, os.path.basename(motion["File"]))
                    resources_to_download.append((motion_url, motion_path))
        
        # 表情文件
        if "Expressions" in refs:
            for expression in refs["Expressions"]:
                expression_url = urljoin(base_url, expression["File"])
                expression_path = os.path.join(expressions_dir, os.path.basename(expression["File"]))
                resources_to_download.append((expression_url, expression_path))
    
    return resources_to_download, json_file_path, model_data

def update_model_json(json_file_path, model_data):
    """更新model3.json文件中的资源路径，使其指向本地目录"""
    if "FileReferences" in model_data:
        refs = model_data["FileReferences"]
        
        # 更新模型文件路径
        if "Moc" in refs:
            refs["Moc"] = os.path.basename(refs["Moc"])
        
        # 更新纹理文件路径
        if "Textures" in refs:
            # 获取textures目录
            textures_dir = os.path.join(os.path.dirname(json_file_path), "textures")
            
            # 检查是否需要转换webp到png
            texture_conversions = {}
            for i, texture in enumerate(refs["Textures"]):
                texture_filename = os.path.basename(texture)
                full_path = os.path.join(textures_dir, texture_filename)
                
                # 如果是webp文件，尝试转换
                if full_path.lower().endswith('.webp'):
                    new_path = convert_webp_to_png(full_path)
                    if new_path != full_path:
                        texture_conversions[i] = os.path.basename(new_path)
            
            # 更新纹理路径
            for i, texture in enumerate(refs["Textures"]):
                if i in texture_conversions:
                    # 使用转换后的png文件名
                    refs["Textures"][i] = "textures/" + texture_conversions[i]
                else:
                    # 使用原始文件名
                    refs["Textures"][i] = "textures/" + os.path.basename(texture)
        
        # 更新物理文件路径
        if "Physics" in refs:
            refs["Physics"] = os.path.basename(refs["Physics"])
        
        # 更新动作文件路径
        if "Motions" in refs:
            for motion_group_name, motion_group in refs["Motions"].items():
                for i, motion in enumerate(motion_group):
                    motion["File"] = f"motions/{motion_group_name}/" + os.path.basename(motion["File"])
        
        # 更新表情文件路径
        if "Expressions" in refs:
            for i, expression in enumerate(refs["Expressions"]):
                expression["File"] = "expressions/" + os.path.basename(expression["File"])
        
        # 保存更新后的JSON文件
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(model_data, f, ensure_ascii=False, indent=2)
        
        logging.info(f"成功更新模型JSON文件: {json_file_path}")

def download_live2d_model(model_url, save_dir):
    """下载Live2D模型及其所有依赖资源"""
    try:
        # 下载并解析主模型文件
        resources, json_file_path, model_data = parse_model_json(model_url, save_dir)
        
        # 使用线程池下载所有资源
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            for resource_url, resource_path in resources:
                executor.submit(download_file, resource_url, resource_path)
        
        # 更新model3.json文件中的资源路径
        update_model_json(json_file_path, model_data)
        
        return True
    except Exception as e:
        logging.error(f"下载模型失败: {model_url}, 错误: {e}")
        return False

def process_character(character):
    """处理单个角色的所有服装模型"""
    char_name = character["charName"]
    logging.info(f"开始处理角色: {char_name}")
    
    for costume in character["live2d"]:
        costume_name = costume["costumeName"]
        model_url = costume["path"]
        
        # 创建角色和服装对应的目录
        costume_dir = os.path.join(DOWNLOAD_DIR, char_name, costume_name)
        ensure_dir(costume_dir)
        
        logging.info(f"开始下载模型: {char_name}/{costume_name}")
        
        if download_live2d_model(model_url, costume_dir):
            logging.info(f"角色 {char_name} 的服装 {costume_name} 下载完成")
        else:
            logging.error(f"角色 {char_name} 的服装 {costume_name} 下载失败")

def main():
    """主函数"""
    try:
        # 读取配置文件
        config_path = os.path.join(BASE_DIR, "config.json")
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                app_config = json.load(f)
            
            # 应用配置
            global DOWNLOAD_DIR, MAX_WORKERS
            DOWNLOAD_DIR = os.path.join(BASE_DIR, app_config.get("download_dir", "downloads"))
            MAX_WORKERS = app_config.get("max_workers", 5)
            
            # 获取测试模式设置
            test_mode = app_config.get("test_mode", False)
        else:
            test_mode = False
        
        # 解析命令行参数
        parser = argparse.ArgumentParser(description="下载碧蓝航线Live2D模型")
        parser.add_argument("--test", action="store_true", help="测试模式，只下载一个皮肤")
        args = parser.parse_args()
        
        # 命令行参数优先级高于配置文件
        if args.test:
            test_mode = True
        
        # 确保下载目录存在
        ensure_dir(DOWNLOAD_DIR)
        
        # 读取模型配置文件
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        if test_mode:
            logging.info("测试模式：只下载第一个皮肤...")
            # 只处理第一个游戏的第一个角色的第一个皮肤
            if config["Master"] and config["Master"][0]["character"]:
                game = config["Master"][0]
                character = game["character"][0]
                if character["live2d"]:
                    costume = character["live2d"][0]
                    logging.info(f"测试下载: 游戏={game['gameName']}, 角色={character['charName']}, 皮肤={costume['costumeName']}")
                    
                    # 创建角色和服装对应的目录
                    costume_dir = os.path.join(DOWNLOAD_DIR, character["charName"], costume["costumeName"])
                    ensure_dir(costume_dir)
                    
                    if download_live2d_model(costume["path"], costume_dir):
                        logging.info(f"测试下载完成: {character['charName']}/{costume['costumeName']}")
                    else:
                        logging.error(f"测试下载失败: {character['charName']}/{costume['costumeName']}")
                else:
                    logging.error("未找到可下载的皮肤")
            else:
                logging.error("未找到可下载的角色")
        else:
            # 常规模式：处理每个游戏的角色
            for game in config["Master"]:
                logging.info(f"开始处理游戏: {game['gameName']}")
                
                # 使用线程池处理每个角色
                with ThreadPoolExecutor(max_workers=3) as executor:
                    for character in game["character"]:
                        executor.submit(process_character, character)
        
        logging.info("所有下载任务完成!")
        
    except Exception as e:
        logging.error(f"程序执行出错: {e}")

if __name__ == "__main__":
    main()
