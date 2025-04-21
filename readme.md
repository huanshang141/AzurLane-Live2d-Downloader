# 碧蓝航线Live2d下载器（Azur Lane  Live2d Downloader）

## 项目简介

本项目能从[Live2D Viewer Online](https://static.l2d.su/live2d)中下载碧蓝航线的live2d文件，并且按照角色进行下载文件的组织

## 主要功能

- 一键下载网站上所有的live2d
- 自动分类整理下载的资源

## 不足

- 网站只提供webp格式的材质，无法在Live2DViewerEX中导入，暂不知道解决方法，所以使用`Pillow`库把webp格式的材质转换为png格式，而这会使得材质占据较大空间
- 因不熟悉python的打包，[releases](https://github.com/huanshang141/AzurLane-Live2d-Downloader/releases)中的可执行文件只有x86-64架构的Windows版本，并且体积巨大

## 部署指南

### 从可执行文件部署
1. 打开[releases](https://github.com/huanshang141/AzurLane-Live2d-Downloader/releases)界面
2. 点击后缀为exe的文件即可下载
3. 下载好后双击运行，会在exe文件的同一目录下生成`download`文件，资源会下载到里面
### 从源码部署
#### 环境准备
1. python 3.10+
2. pip
3. （可选）conda或其他python环境管理工具
#### 获取源码
可选下面任一方法
##### 通过git
在你喜欢的路径下打开cmd或终端，然后运行
```bash
git clone https://github.com/huanshang141/AzurLane-Live2d-Downloader.git
cd AzurLane-Live2d-Downloader
```
##### 通过下载压缩包
点击绿色的Code，然后Download ZIP，下载完后解压，然后打开AzurLane-Live2d-Downloader文件夹
![这是图片](https://github.com/huanshang141/AzurLane-Live2d-Downloader/blob/main/doc/pic/1.png)
#### 安装依赖
运行
```bash
pip install -r requirements.txt
```
#### 运行程序
```bash
python download.py
```

## TODO
- [ ] 图形界面
- [ ] 可选资源下载
- [ ] 静态立绘下载
- [ ] ...
## 贡献指南

欢迎提交Issue和Pull Request，共同改进这个项目！

## 免责声明

本工具仅用于个人学习和研究，所有下载的资源来自互联网，版权归游戏开发商所有。请勿用于商业用途。

### 联系方式

如有问题或建议，请通过以下方式联系：
- GitHub Issues: [提交问题](https://github.com/huanshang141/AzurLane-Live2d-Downloader/issues)
