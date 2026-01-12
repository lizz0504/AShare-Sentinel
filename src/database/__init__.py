# -*- coding: utf-8 -*-
"""
AShare-Sentinel 数据库模块
"""

from .database import (
    init_db,
    save_analysis,
    get_analysis_today,
    get_latest_analysis,
    get_all_analyses,
    delete_analysis,
    update_status,
    get_records,
    get_records_by_status,
    get_statistics
)

__all__ = [
    'init_db',
    'save_analysis',
    'get_analysis_today',
    'get_latest_analysis',
    'get_all_analyses',
    'delete_analysis',
    'update_status',
    'get_records',
    'get_records_by_status',
    'get_statistics'
]
