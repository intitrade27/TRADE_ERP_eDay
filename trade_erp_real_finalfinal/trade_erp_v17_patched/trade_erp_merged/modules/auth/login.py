# -*- coding: utf-8 -*-
"""로그인 모듈"""
import hashlib
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple
import pandas as pd

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config.settings import DATA_DIR

logger = logging.getLogger(__name__)
USERS_FILE = DATA_DIR / "users.xlsx"

class AuthError(Exception):
    pass

def _hash_password(pw: str) -> str:
    return hashlib.sha256(pw.encode('utf-8')).hexdigest()

def _ensure_users_file() -> pd.DataFrame:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not USERS_FILE.exists():
        df = pd.DataFrame(columns=['user_id', 'password_hash', 'name', 'role', 'created_date', 'last_login'])
        df.to_excel(USERS_FILE, index=False, engine='openpyxl')
        return df
    return pd.read_excel(USERS_FILE, engine='openpyxl')

def _save_users(df: pd.DataFrame):
    df.to_excel(USERS_FILE, index=False, engine='openpyxl')

def register_user(user_id: str, password: str, name: str, role: str = "user") -> bool:
    df = _ensure_users_file()
    if user_id in df['user_id'].values:
        raise AuthError(f"ID 중복: {user_id}")
    new = {'user_id': user_id, 'password_hash': _hash_password(password), 'name': name, 'role': role, 'created_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'last_login': None}
    df = pd.concat([df, pd.DataFrame([new])], ignore_index=True)
    _save_users(df)
    return True

def authenticate(user_id: str, password: str) -> Tuple[bool, Optional[dict]]:
    df = _ensure_users_file()
    user = df[df['user_id'] == user_id]
    if user.empty or user.iloc[0]['password_hash'] != _hash_password(password):
        return False, None
    df.loc[df['user_id'] == user_id, 'last_login'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    _save_users(df)
    return True, {'user_id': user.iloc[0]['user_id'], 'name': user.iloc[0]['name'], 'role': user.iloc[0]['role']}

def init_default_admin():
    df = _ensure_users_file()
    if 'admin' not in df['user_id'].values:
        register_user('admin', 'admin123', '관리자', 'admin')

def get_all_users() -> pd.DataFrame:
    """전체 사용자 목록 조회"""
    return _ensure_users_file()

def change_password(user_id: str, old_pw: str, new_pw: str) -> bool:
    ok, _ = authenticate(user_id, old_pw)
    if not ok:
        return False
    df = _ensure_users_file()
    df.loc[df['user_id'] == user_id, 'password_hash'] = _hash_password(new_pw)
    _save_users(df)
    return True
