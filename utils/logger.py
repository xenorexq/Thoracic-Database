"""
应用程序日志模块

提供简单的文件日志功能，用于诊断打包后的问题。
"""

from __future__ import annotations

import sys
import logging
from pathlib import Path
from datetime import datetime


def setup_logger(name: str = "thoracic_app", log_file: str = "app.log") -> logging.Logger:
    """
    设置应用程序日志器
    
    Args:
        name: 日志器名称
        log_file: 日志文件名
    
    Returns:
        配置好的日志器
    """
    logger = logging.getLogger(name)
    
    # 如果已经配置过，直接返回
    if logger.handlers:
        return logger
    
    logger.setLevel(logging.DEBUG)
    
    # 文件处理器
    try:
        log_path = Path(log_file)
        file_handler = logging.FileHandler(log_path, encoding='utf-8', mode='a')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"Warning: Failed to create file handler: {e}")
    
    # 控制台处理器
    try:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '[%(levelname)s] %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
    except Exception as e:
        print(f"Warning: Failed to create console handler: {e}")
    
    # 记录启动信息
    logger.info("=" * 60)
    logger.info(f"应用程序启动 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Python 版本: {sys.version}")
    logger.info(f"工作目录: {Path.cwd()}")
    logger.info("=" * 60)
    
    return logger


# 全局日志器实例
app_logger = setup_logger()


def log_error(message: str, exception: Exception = None):
    """记录错误信息"""
    app_logger.error(message)
    if exception:
        import traceback
        app_logger.error(f"异常详情:\n{traceback.format_exc()}")


def log_info(message: str):
    """记录信息"""
    app_logger.info(message)


def log_debug(message: str):
    """记录调试信息"""
    app_logger.debug(message)


def log_warning(message: str):
    """记录警告信息"""
    app_logger.warning(message)

