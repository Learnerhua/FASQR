#!/bin/bash
echo "========================================"
echo "安装 Playwright 系统依赖"
echo "========================================"

echo "1. 更新包列表..."
sudo apt-get update

echo "2. 安装系统依赖..."
sudo apt-get install -y \
    libnspr4 libnss3 libdrm2 libgbm1 \
    libpango-1.0-0 libcairo2 libglib2.0-0 \
    libasound2t64 \
    libatk1.0-0t64 libatk-bridge2.0-0t64 libatspi2.0-0t64 \
    libgtk-3-0 libgdk-pixbuf-2.0-0 \
    libcups2t64 \
    libx11-6 libx11-xcb1 libxcb1 libxcb-dri3-0 libxcb-shm0 \
    libxcb-xfixes0 libxcb-randr0 libxcb-composite0 libxcb-shape0 \
    libxcomposite1 libxdamage1 libxext6 libxfixes3 libxi6 \
    libxkbcommon0 libxrandr2 libxrender1 libxss1 libxtst6

echo "3. 安装 Playwright Python 包..."
pip install playwright

echo "4. 安装 Playwright 浏览器..."
playwright install chromium

echo "========================================"
echo "安装完成！"
echo "========================================"