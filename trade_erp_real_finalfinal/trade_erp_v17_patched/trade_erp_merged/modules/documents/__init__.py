# -*- coding: utf-8 -*-
"""
서류 생성 모듈
"""

from .generator import (
    DocumentGenerator,
    generate_all_documents,
)

__all__ = [
    'DocumentGenerator',
    'generate_all_documents',
]