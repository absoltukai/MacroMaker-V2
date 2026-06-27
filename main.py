"""
MacroMaker V2 - Main Entry Point
高性能なGUIマクロソフト
"""

import sys
import os
import logging
from pathlib import Path

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def setup_application_directories():
    """アプリケーション用のディレクトリを初期化"""
    app_data_dir = Path.home() / "AppData" / "Local" / "MacroMaker"
    projects_dir = app_data_dir / "projects"
    backups_dir = app_data_dir / "backups"
    logs_dir = app_data_dir / "logs"
    
    for directory in [app_data_dir, projects_dir, backups_dir, logs_dir]:
        directory.mkdir(parents=True, exist_ok=True)
    
    return {
        'app_data': app_data_dir,
        'projects': projects_dir,
        'backups': backups_dir,
        'logs': logs_dir
    }


def check_dependencies():
    """必要なモジュールの依存性をチェック"""
    required_modules = {
        'tkinter': 'tkinter',
        'json': 'json',
        'threading': 'threading',
        'pynput': 'pynput (キーボード・マウス制御用)',
    }
    
    missing_modules = []
    
    for module_name, display_name in required_modules.items():
        try:
            __import__(module_name)
            logger.info(f"✓ {display_name} - OK")
        except ImportError:
            missing_modules.append(display_name)
            logger.warning(f"✗ {display_name} - NOT FOUND")
    
    if missing_modules:
        error_msg = "以下のモジュールがインストールされていません:\n"
        error_msg += "\n".join(f"  - {mod}" for mod in missing_modules)
        error_msg += "\n\n以下のコマンドでインストールしてください:\n"
        error_msg += "pip install pynput"
        
        logger.error(error_msg)
        
        # GUI でも警告を表示する
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("依存性エラー", error_msg)
            root.destroy()
        except:
            pass
        
        return False
    
    return True


def initialize_application():
    """アプリケーションの初期化"""
    try:
        logger.info("=" * 60)
        logger.info("MacroMaker V2 - Starting up")
        logger.info("=" * 60)
        
        # ディレクトリ初期化
        logger.info("Setting up application directories...")
        app_dirs = setup_application_directories()
        logger.info(f"App data directory: {app_dirs['app_data']}")
        
        # 依存性チェック
        logger.info("Checking dependencies...")
        if not check_dependencies():
            return None
        
        # GUI のインポート
        logger.info("Importing GUI module...")
        from gui import MacroMakerGUI
        
        # GUI 起動
        logger.info("Launching GUI...")
        gui = MacroMakerGUI(app_dirs)
        
        logger.info("Application initialized successfully")
        return gui
        
    except Exception as e:
        logger.error(f"Failed to initialize application: {e}", exc_info=True)
        return None


def main():
    """メイン処理"""
    try:
        gui = initialize_application()
        
        if gui is None:
            logger.error("Failed to initialize application")
            sys.exit(1)
        
        # GUI を起動
        logger.info("Running GUI main loop...")
        gui.run()
        
        logger.info("MacroMaker V2 - Shutdown complete")
        
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
