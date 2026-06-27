"""
MacroMaker V2 - Settings Manager
アプリケーション設定の管理
"""

import json
import logging
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class ThemeSettings:
    """テーマ設定"""
    mode: str = "dark"  # "dark" or "light"
    
    # ダークモード用色
    dark_bg: str = "#1e1e1e"
    dark_fg: str = "#ffffff"
    dark_accent: str = "#0078d4"
    dark_hover: str = "#2d2d2d"
    dark_border: str = "#3e3e3e"
    
    # ライトモード用色
    light_bg: str = "#ffffff"
    light_fg: str = "#000000"
    light_accent: str = "#0078d4"
    light_hover: str = "#f0f0f0"
    light_border: str = "#e0e0e0"
    
    def get_colors(self) -> Dict[str, str]:
        """現在のテーマに応じた色セットを取得"""
        if self.mode == "dark":
            return {
                "bg": self.dark_bg,
                "fg": self.dark_fg,
                "accent": self.dark_accent,
                "hover": self.dark_hover,
                "border": self.dark_border,
            }
        else:
            return {
                "bg": self.light_bg,
                "fg": self.light_fg,
                "accent": self.light_accent,
                "hover": self.light_hover,
                "border": self.light_border,
            }


@dataclass
class UISettings:
    """UI設定"""
    window_width: int = 1200
    window_height: int = 800
    window_x: int = 100
    window_y: int = 100
    theme: ThemeSettings = field(default_factory=ThemeSettings)
    font_size: int = 10
    show_line_numbers: bool = True
    auto_save_interval: int = 60  # 秒


@dataclass
class ExecutionSettings:
    """実行設定"""
    countdown_seconds: int = 3
    emergency_stop_key: str = "esc"  # Escキーで緊急停止
    emergency_stop_count: int = 3  # 3回連続で停止
    enable_highlighting: bool = True
    show_remaining_loops: bool = True


@dataclass
class RecorderSettings:
    """録画設定"""
    auto_record_delay: bool = True
    min_delay_ms: int = 10
    max_delay_ms: int = 500
    smooth_mouse_movement: bool = True


@dataclass
class ProjectSettings:
    """プロジェクト設定"""
    auto_save: bool = True
    create_backups: bool = True
    backup_count: int = 10  # 保持するバックアップ数
    compress_backups: bool = True


@dataclass
class AppSettings:
    """アプリケーション全体の設定"""
    ui: UISettings = field(default_factory=UISettings)
    execution: ExecutionSettings = field(default_factory=ExecutionSettings)
    recorder: RecorderSettings = field(default_factory=RecorderSettings)
    project: ProjectSettings = field(default_factory=ProjectSettings)
    
    # その他の設定
    log_level: str = "INFO"
    language: str = "ja"  # 将来的に多言語対応
    check_updates: bool = True
    telemetry_enabled: bool = False


class SettingsManager:
    """設定の読み書きを管理"""
    
    SETTINGS_FILENAME = "settings.json"
    
    def __init__(self, app_data_dir: Path):
        """
        初期化
        
        Args:
            app_data_dir: アプリケーションデータディレクトリ
        """
        self.app_data_dir = Path(app_data_dir)
        self.settings_file = self.app_data_dir / self.SETTINGS_FILENAME
        self.settings = AppSettings()
        
        # 設定を読み込む
        self._load_settings()
    
    def _load_settings(self) -> None:
        """ファイルから設定を読み込む"""
        try:
            if self.settings_file.exists():
                logger.info(f"Loading settings from {self.settings_file}")
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._deserialize_settings(data)
                logger.info("Settings loaded successfully")
            else:
                logger.info("Settings file not found, using defaults")
                self._save_settings()
        except Exception as e:
            logger.error(f"Failed to load settings: {e}")
            logger.warning("Using default settings")
            self.settings = AppSettings()
            self._save_settings()
    
    def _deserialize_settings(self, data: Dict[str, Any]) -> None:
        """辞書から設定オブジェクトを生成"""
        try:
            # UI設定
            ui_data = data.get("ui", {})
            theme_data = ui_data.get("theme", {})
            self.settings.ui.theme = ThemeSettings(**theme_data)
            for key, value in ui_data.items():
                if key != "theme" and hasattr(self.settings.ui, key):
                    setattr(self.settings.ui, key, value)
            
            # 実行設定
            exec_data = data.get("execution", {})
            for key, value in exec_data.items():
                if hasattr(self.settings.execution, key):
                    setattr(self.settings.execution, key, value)
            
            # 録画設定
            recorder_data = data.get("recorder", {})
            for key, value in recorder_data.items():
                if hasattr(self.settings.recorder, key):
                    setattr(self.settings.recorder, key, value)
            
            # プロジェクト設定
            project_data = data.get("project", {})
            for key, value in project_data.items():
                if hasattr(self.settings.project, key):
                    setattr(self.settings.project, key, value)
            
            # その他の設定
            if "log_level" in data:
                self.settings.log_level = data["log_level"]
            if "language" in data:
                self.settings.language = data["language"]
            if "check_updates" in data:
                self.settings.check_updates = data["check_updates"]
            if "telemetry_enabled" in data:
                self.settings.telemetry_enabled = data["telemetry_enabled"]
        
        except Exception as e:
            logger.error(f"Error deserializing settings: {e}")
    
    def _save_settings(self) -> None:
        """設定をファイルに保存"""
        try:
            data = {
                "ui": self._serialize_dataclass(self.settings.ui),
                "execution": asdict(self.settings.execution),
                "recorder": asdict(self.settings.recorder),
                "project": asdict(self.settings.project),
                "log_level": self.settings.log_level,
                "language": self.settings.language,
                "check_updates": self.settings.check_updates,
                "telemetry_enabled": self.settings.telemetry_enabled,
            }
            
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Settings saved to {self.settings_file}")
        
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
    
    def _serialize_dataclass(self, obj: Any) -> Dict[str, Any]:
        """dataclassオブジェクトを辞書にシリアライズ"""
        result = {}
        for key, value in asdict(obj).items():
            if isinstance(value, ThemeSettings):
                result[key] = asdict(value)
            else:
                result[key] = value
        return result
    
    def save(self) -> None:
        """現在の設定を保存"""
        self._save_settings()
    
    def reset_to_defaults(self) -> None:
        """設定をデフォルト値にリセット"""
        logger.info("Resetting settings to defaults")
        self.settings = AppSettings()
        self._save_settings()
    
    def get_theme_colors(self) -> Dict[str, str]:
        """現在のテーマの色セットを取得"""
        return self.settings.ui.theme.get_colors()
    
    def set_theme_mode(self, mode: str) -> None:
        """テーマモードを設定 ("dark" or "light")"""
        if mode in ("dark", "light"):
            self.settings.ui.theme.mode = mode
            self._save_settings()
            logger.info(f"Theme mode changed to {mode}")
        else:
            logger.warning(f"Invalid theme mode: {mode}")
    
    def set_window_geometry(self, x: int, y: int, width: int, height: int) -> None:
        """ウィンドウの位置とサイズを保存"""
        self.settings.ui.window_x = x
        self.settings.ui.window_y = y
        self.settings.ui.window_width = width
        self.settings.ui.window_height = height
        self._save_settings()
    
    def get_window_geometry(self) -> tuple:
        """ウィンドウの位置とサイズを取得"""
        return (
            self.settings.ui.window_x,
            self.settings.ui.window_y,
            self.settings.ui.window_width,
            self.settings.ui.window_height,
        )
    
    def __repr__(self) -> str:
        """設定内容を文字列表現"""
        return json.dumps(
            {
                "ui": self._serialize_dataclass(self.settings.ui),
                "execution": asdict(self.settings.execution),
                "recorder": asdict(self.settings.recorder),
                "project": asdict(self.settings.project),
            },
            indent=2,
            ensure_ascii=False,
        )
