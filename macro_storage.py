"""
MacroMaker V2 - Macro Storage Manager
マクロの保存・読み込み・バックアップ管理
"""

import json
import logging
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any
from macro_actions import MacroAction, ActionFactory

logger = logging.getLogger(__name__)


class MacroProject:
    """マクロプロジェクト"""
    
    def __init__(self, name: str, description: str = "", icon: str = "📋"):
        self.name = name
        self.description = description
        self.icon = icon
        self.macros: List['Macro'] = []
        self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()
    
    def add_macro(self, macro: 'Macro') -> None:
        """マクロを追加"""
        self.macros.append(macro)
        self.updated_at = datetime.now().isoformat()
    
    def remove_macro(self, macro_name: str) -> bool:
        """マクロを削除"""
        for i, macro in enumerate(self.macros):
            if macro.name == macro_name:
                self.macros.pop(i)
                self.updated_at = datetime.now().isoformat()
                return True
        return False
    
    def get_macro(self, macro_name: str) -> Optional['Macro']:
        """マクロを取得"""
        for macro in self.macros:
            if macro.name == macro_name:
                return macro
        return None
    
    def to_dict(self) -> dict:
        """辞書に変換"""
        return {
            "name": self.name,
            "description": self.description,
            "icon": self.icon,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "macros": [macro.to_dict() for macro in self.macros]
        }


class Macro:
    """マクロ"""
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.actions: List[MacroAction] = []
        self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()
    
    def add_action(self, action: MacroAction, index: Optional[int] = None) -> None:
        """アクションを追加"""
        if index is None:
            self.actions.append(action)
        else:
            self.actions.insert(index, action)
        self._renumber_actions()
        self.updated_at = datetime.now().isoformat()
    
    def remove_action(self, index: int) -> bool:
        """アクションを削除"""
        if 0 <= index < len(self.actions):
            self.actions.pop(index)
            self._renumber_actions()
            self.updated_at = datetime.now().isoformat()
            return True
        return False
    
    def get_action(self, index: int) -> Optional[MacroAction]:
        """アクションを取得"""
        if 0 <= index < len(self.actions):
            return self.actions[index]
        return None
    
    def _renumber_actions(self) -> None:
        """アクションの行番号を付け直す"""
        for i, action in enumerate(self.actions):
            action.line_number = i + 1
    
    def to_dict(self) -> dict:
        """辞書に変換"""
        return {
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "actions": [action.to_dict() for action in self.actions]
        }
    
    @staticmethod
    def from_dict(data: dict) -> 'Macro':
        """辞書からマクロを生成"""
        macro = Macro(
            name=data["name"],
            description=data.get("description", "")
        )
        macro.created_at = data.get("created_at", macro.created_at)
        macro.updated_at = data.get("updated_at", macro.updated_at)
        
        for action_data in data.get("actions", []):
            action = ActionFactory.create_from_dict(action_data)
            macro.actions.append(action)
        
        macro._renumber_actions()
        return macro


class MacroStorageManager:
    """マクロの保存・読み込みを管理"""
    
    PROJECT_EXTENSION = ".mmp"  # MacroMaker Project
    MACRO_EXTENSION = ".mma"    # MacroMaker Action
    BACKUP_EXTENSION = ".backup"
    
    def __init__(self, projects_dir: Path, backups_dir: Path):
        """
        初期化
        
        Args:
            projects_dir: プロジェクト保存ディレクトリ
            backups_dir: バックアップディレクトリ
        """
        self.projects_dir = Path(projects_dir)
        self.backups_dir = Path(backups_dir)
        self.projects_dir.mkdir(parents=True, exist_ok=True)
        self.backups_dir.mkdir(parents=True, exist_ok=True)
    
    def save_project(self, project: MacroProject, project_name: str) -> bool:
        """プロジェクトを保存"""
        try:
            project_path = self.projects_dir / f"{project_name}{self.PROJECT_EXTENSION}"
            
            # バックアップを作成
            if project_path.exists():
                self._create_backup(project_path)
            
            with open(project_path, 'w', encoding='utf-8') as f:
                json.dump(project.to_dict(), f, indent=2, ensure_ascii=False)
            
            logger.info(f"Project saved: {project_path}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to save project: {e}")
            return False
    
    def load_project(self, project_name: str) -> Optional[MacroProject]:
        """プロジェクトを読み込む"""
        try:
            project_path = self.projects_dir / f"{project_name}{self.PROJECT_EXTENSION}"
            
            if not project_path.exists():
                logger.warning(f"Project file not found: {project_path}")
                return None
            
            with open(project_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            project = MacroProject(
                name=data["name"],
                description=data.get("description", ""),
                icon=data.get("icon", "📋")
            )
            project.created_at = data.get("created_at", project.created_at)
            project.updated_at = data.get("updated_at", project.updated_at)
            
            for macro_data in data.get("macros", []):
                macro = Macro.from_dict(macro_data)
                project.macros.append(macro)
            
            logger.info(f"Project loaded: {project_path}")
            return project
        
        except Exception as e:
            logger.error(f"Failed to load project: {e}")
            return None
    
    def save_macro(self, macro: Macro, macro_name: str) -> bool:
        """単一のマクロを保存（非プロジェクト）"""
        try:
            macro_path = self.projects_dir / f"{macro_name}{self.MACRO_EXTENSION}"
            
            if macro_path.exists():
                self._create_backup(macro_path)
            
            with open(macro_path, 'w', encoding='utf-8') as f:
                json.dump(macro.to_dict(), f, indent=2, ensure_ascii=False)
            
            logger.info(f"Macro saved: {macro_path}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to save macro: {e}")
            return False
    
    def load_macro(self, macro_name: str) -> Optional[Macro]:
        """単一のマクロを読み込む"""
        try:
            macro_path = self.projects_dir / f"{macro_name}{self.MACRO_EXTENSION}"
            
            if not macro_path.exists():
                logger.warning(f"Macro file not found: {macro_path}")
                return None
            
            with open(macro_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            macro = Macro.from_dict(data)
            logger.info(f"Macro loaded: {macro_path}")
            return macro
        
        except Exception as e:
            logger.error(f"Failed to load macro: {e}")
            return None
    
    def list_projects(self) -> List[str]:
        """プロジェクト一覧を取得"""
        projects = []
        for file in self.projects_dir.glob(f"*{self.PROJECT_EXTENSION}"):
            projects.append(file.stem)
        return sorted(projects)
    
    def list_macros(self) -> List[str]:
        """マクロ一覧を取得"""
        macros = []
        for file in self.projects_dir.glob(f"*{self.MACRO_EXTENSION}"):
            macros.append(file.stem)
        return sorted(macros)
    
    def delete_project(self, project_name: str) -> bool:
        """プロジェクトを削除"""
        try:
            project_path = self.projects_dir / f"{project_name}{self.PROJECT_EXTENSION}"
            if project_path.exists():
                project_path.unlink()
                logger.info(f"Project deleted: {project_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete project: {e}")
            return False
    
    def delete_macro(self, macro_name: str) -> bool:
        """マクロを削除"""
        try:
            macro_path = self.projects_dir / f"{macro_name}{self.MACRO_EXTENSION}"
            if macro_path.exists():
                macro_path.unlink()
                logger.info(f"Macro deleted: {macro_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete macro: {e}")
            return False
    
    def _create_backup(self, file_path: Path, max_backups: int = 10) -> bool:
        """バックアップを作成し、古いものは削除"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{file_path.stem}_{timestamp}{self.BACKUP_EXTENSION}"
            backup_path = self.backups_dir / backup_name
            
            shutil.copy2(file_path, backup_path)
            logger.info(f"Backup created: {backup_path}")
            
            # 古いバックアップを削除
            backups = sorted(self.backups_dir.glob(f"{file_path.stem}_*{self.BACKUP_EXTENSION}"))
            if len(backups) > max_backups:
                for old_backup in backups[:-max_backups]:
                    old_backup.unlink()
                    logger.info(f"Old backup deleted: {old_backup}")
            
            return True
        
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return False
    
    def restore_backup(self, backup_name: str, restore_path: Path) -> bool:
        """バックアップから復元"""
        try:
            backup_path = self.backups_dir / f"{backup_name}{self.BACKUP_EXTENSION}"
            if not backup_path.exists():
                logger.warning(f"Backup not found: {backup_path}")
                return False
            
            shutil.copy2(backup_path, restore_path)
            logger.info(f"Restored from backup: {backup_path}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to restore backup: {e}")
            return False
    
    def list_backups(self) -> List[str]:
        """バックアップ一覧を取得"""
        backups = []
        for file in self.backups_dir.glob(f"*{self.BACKUP_EXTENSION}"):
            backups.append(file.stem)
        return sorted(backups, reverse=True)
