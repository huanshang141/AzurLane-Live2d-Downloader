import subprocess
import sys

def install_requirements():
    """安装打包所需的依赖"""
    requirements = [
        "pyinstaller",
        "requests",
        "pillow"
    ]
    
    print("正在安装所需依赖...")
    for package in requirements:
        print(f"安装 {package}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
    
    print("所有依赖安装完成！")

if __name__ == "__main__":
    install_requirements()
