"""
MacroMaker V2 - GUI Application
メインGUIアプリケーション（tkinter）
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

from settings import SettingsManager
from macro_storage import MacroStorageManager, MacroProject, Macro
from macro_actions import MacroAction, ActionFactory, ActionType, get_action_info
from macro_engine import MacroExecutor, ExecutionState
from recorder import MacroRecorder, RecorderState

logger = logging.getLogger(__name__)


class MacroMakerGUI:
    """MacroMaker V2 メインGUI"""
    
    def __init__(self, app_dirs: dict):
        """
        初期化
        
        Args:
            app_dirs: アプリケーションディレクトリ辞書
        """
        self.app_dirs = app_dirs
        
        # 設定管理
        self.settings_manager = SettingsManager(app_dirs['app_data'])
        
        # ストレージ管理
        self.storage_manager = MacroStorageManager(
            app_dirs['projects'],
            app_dirs['backups']
        )
        
        # 現在のプロジェクト・マクロ
        self.current_project: Optional[MacroProject] = None
        self.current_macro: Optional[Macro] = None
        
        # 実行エンジン・レコーダー
        self.executor: Optional[MacroExecutor] = None
        self.recorder: Optional[MacroRecorder] = None
        
        # GUI ウィンドウ
        self.root = tk.Tk()
        self.root.title("MacroMaker V2")
        
        # ウィンドウサイズ復元
        x, y, w, h = self.settings_manager.get_window_geometry()
        self.root.geometry(f"{w}x{h}+{x}+{y}")
        
        # 色設定
        self.colors = self.settings_manager.get_theme_colors()
        self.root.configure(bg=self.colors['bg'])
        
        # GUI 構築
        self._setup_ui()
        
        logger.info("GUI initialized")
    
    def _setup_ui(self) -> None:
        """UIの構築"""
        # メニューバー
        self._setup_menu()
        
        # ツールバー
        self._setup_toolbar()
        
        # メインレイアウト（左パネル + 中央 + 右パネル）
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 左パネル：プロジェクト・マクロツリー
        self.left_frame = self._setup_left_panel(main_frame)
        
        # 中央パネル：アクションエディタ
        self.center_frame = self._setup_center_panel(main_frame)
        
        # 右パネル：プロパティ・ログ
        self.right_frame = self._setup_right_panel(main_frame)
        
        # ステータスバー
        self._setup_statusbar()
    
    def _setup_menu(self) -> None:
        """メニューバーの構築"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # ファイルメニュー
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="ファイル", menu=file_menu)
        file_menu.add_command(label="新規プロジェクト", command=self._new_project)
        file_menu.add_command(label="プロジェクト打ち開く", command=self._open_project)
        file_menu.add_command(label="プロジェクト保存", command=self._save_project)
        file_menu.add_separator()
        file_menu.add_command(label="終了", command=self.root.quit)
        
        # 編集メニュー
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="編集", menu=edit_menu)
        edit_menu.add_command(label="元に戻す", command=self._undo)
        edit_menu.add_command(label="やり直す", command=self._redo)
        edit_menu.add_separator()
        edit_menu.add_command(label="設定", command=self._open_settings)
        
        # マクロメニュー
        macro_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="マクロ", menu=macro_menu)
        macro_menu.add_command(label="新規マクロ", command=self._new_macro)
        macro_menu.add_command(label="マクロ削除", command=self._delete_macro)
        
        # ヘルプメニュー
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="ヘルプ", menu=help_menu)
        help_menu.add_command(label="バージョン情報", command=self._show_about)
    
    def _setup_toolbar(self) -> None:
        """ツールバーの構築"""
        toolbar = ttk.Frame(self.root)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        # 実行ボタン
        self.btn_execute = ttk.Button(toolbar, text="▶ 実行", command=self._execute_macro)
        self.btn_execute.pack(side=tk.LEFT, padx=2)
        
        # 一時停止ボタン
        self.btn_pause = ttk.Button(toolbar, text="⏸ 一時停止", command=self._pause_macro)
        self.btn_pause.pack(side=tk.LEFT, padx=2)
        
        # 停止ボタン
        self.btn_stop = ttk.Button(toolbar, text="⏹ 停止", command=self._stop_macro)
        self.btn_stop.pack(side=tk.LEFT, padx=2)
        
        # 区切り
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        # 記録ボタン
        self.btn_record = ttk.Button(toolbar, text="● 記録", command=self._start_recording)
        self.btn_record.pack(side=tk.LEFT, padx=2)
        
        # 記録停止ボタン
        self.btn_record_stop = ttk.Button(toolbar, text="◻ 記録停止", command=self._stop_recording)
        self.btn_record_stop.pack(side=tk.LEFT, padx=2)
    
    def _setup_left_panel(self, parent) -> ttk.Frame:
        """左パネル（プロジェクト・マクロツリー）の構築"""
        frame = ttk.LabelFrame(parent, text="プロジェクト", width=200)
        frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=5, pady=5)
        
        # ツリービュー
        self.project_tree = ttk.Treeview(frame, height=20)
        self.project_tree.pack(fill=tk.BOTH, expand=True)
        self.project_tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        
        return frame
    
    def _setup_center_panel(self, parent) -> ttk.Frame:
        """中央パネル（アクションエディタ）の構築"""
        frame = ttk.LabelFrame(parent, text="アクション")
        frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # ツールバー
        toolbar = ttk.Frame(frame)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(toolbar, text="+ キー入力", command=self._add_key_action).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="+ 文字入力", command=self._add_text_action).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="+ 待機", command=self._add_wait_action).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="+ ループ", command=self._add_loop_action).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="削除", command=self._delete_action).pack(side=tk.LEFT, padx=2)
        
        # アクションリスト
        self.action_listbox = tk.Listbox(frame, height=15)
        self.action_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.action_listbox.bind("<<ListboxSelect>>", self._on_action_select)
        
        return frame
    
    def _setup_right_panel(self, parent) -> ttk.Frame:
        """右パネル（プロパティ・ログ）の構築"""
        frame = ttk.Frame(parent)
        frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # プロパティフレーム
        prop_frame = ttk.LabelFrame(frame, text="プロパティ")
        prop_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.property_text = tk.Text(prop_frame, height=8, width=30)
        self.property_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # ログフレーム
        log_frame = ttk.LabelFrame(frame, text="ログ")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.log_text = tk.Text(log_frame, height=10, width=30)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        return frame
    
    def _setup_statusbar(self) -> None:
        """ステータスバーの構築"""
        self.statusbar = ttk.Label(self.root, text="準備完了", relief=tk.SUNKEN)
        self.statusbar.pack(side=tk.BOTTOM, fill=tk.X)
    
    # ===== イベントハンドラ =====
    
    def _new_project(self) -> None:
        """新規プロジェクト"""
        name = tk.simpledialog.askstring("新規プロジェクト", "プロジェクト名:")
        if name:
            self.current_project = MacroProject(name)
            self._refresh_tree()
            self._log(f"プロジェクト作成: {name}")
    
    def _open_project(self) -> None:
        """プロジェクト打ち開く"""
        projects = self.storage_manager.list_projects()
        if not projects:
            messagebox.showwarning("警告", "保存されたプロジェクトがありません")
            return
        
        # プロジェクト選択ダイアログ（簡易版）
        project_name = projects[0]
        self.current_project = self.storage_manager.load_project(project_name)
        if self.current_project:
            self._refresh_tree()
            self._log(f"プロジェクト開く: {project_name}")
    
    def _save_project(self) -> None:
        """プロジェクト保存"""
        if self.current_project:
            self.storage_manager.save_project(self.current_project, self.current_project.name)
            self._log(f"プロジェクト保存: {self.current_project.name}")
            messagebox.showinfo("成功", "プロジェクトを保存しました")
    
    def _new_macro(self) -> None:
        """新規マクロ"""
        if not self.current_project:
            messagebox.showwarning("警告", "プロジェクトを選択してください")
            return
        
        name = tk.simpledialog.askstring("新規マクロ", "マクロ名:")
        if name:
            macro = Macro(name)
            self.current_project.add_macro(macro)
            self.current_macro = macro
            self._refresh_tree()
            self._refresh_action_list()
            self._log(f"マクロ作成: {name}")
    
    def _delete_macro(self) -> None:
        """マクロ削除"""
        if self.current_macro and self.current_project:
            if messagebox.askyesno("確認", f"マクロ '{self.current_macro.name}' を削除しますか？"):
                self.current_project.remove_macro(self.current_macro.name)
                self.current_macro = None
                self._refresh_tree()
                self._log(f"マクロ削除: {self.current_macro.name if self.current_macro else 'Unknown'}")
    
    def _add_key_action(self) -> None:
        """キー入力アクションを追加"""
        if not self.current_macro:
            messagebox.showwarning("警告", "マクロを選択してください")
            return
        
        action = ActionFactory.create_key_input("a")
        self.current_macro.add_action(action)
        self._refresh_action_list()
        self._log("キー入力アクション追加")
    
    def _add_text_action(self) -> None:
        """文字列入力アクションを追加"""
        if not self.current_macro:
            messagebox.showwarning("警告", "マクロを選択してください")
            return
        
        action = ActionFactory.create_text_input("Hello")
        self.current_macro.add_action(action)
        self._refresh_action_list()
        self._log("文字列入力アクション追加")
    
    def _add_wait_action(self) -> None:
        """待機アクションを追加"""
        if not self.current_macro:
            messagebox.showwarning("警告", "マクロを選択してください")
            return
        
        action = ActionFactory.create_wait(1000)
        self.current_macro.add_action(action)
        self._refresh_action_list()
        self._log("待機アクション追加")
    
    def _add_loop_action(self) -> None:
        """ループアクションを追加"""
        if not self.current_macro:
            messagebox.showwarning("警告", "マクロを選択してください")
            return
        
        loop_start = ActionFactory.create_loop_start(5)
        loop_end = ActionFactory.create_loop_end()
        self.current_macro.add_action(loop_start)
        self.current_macro.add_action(loop_end)
        self._refresh_action_list()
        self._log("ループアクション追加")
    
    def _delete_action(self) -> None:
        """選択アクションを削除"""
        if not self.current_macro:
            return
        
        selection = self.action_listbox.curselection()
        if selection:
            index = selection[0]
            self.current_macro.remove_action(index)
            self._refresh_action_list()
            self._log(f"アクション削除: 行{index+1}")
    
    def _execute_macro(self) -> None:
        """マクロを実行"""
        if not self.current_macro:
            messagebox.showwarning("警告", "マクロを選択してください")
            return
        
        self.executor = MacroExecutor(
            self.current_macro.actions,
            on_log=self._log
        )
        self.executor.start()
    
    def _pause_macro(self) -> None:
        """マクロを一時停止"""
        if self.executor:
            self.executor.pause()
    
    def _stop_macro(self) -> None:
        """マクロを停止"""
        if self.executor:
            self.executor.stop()
    
    def _start_recording(self) -> None:
        """記録を開始"""
        if not self.current_macro:
            messagebox.showwarning("警告", "マクロを選択してください")
            return
        
        self.recorder = MacroRecorder(
            on_action_recorded=self._on_action_recorded,
            on_log=self._log
        )
        self.recorder.start()
        messagebox.showinfo("記録開始", "記録を開始しました。Esc キーで停止します。")
    
    def _stop_recording(self) -> None:
        """記録を停止"""
        if self.recorder:
            self.recorder.stop()
            actions = self.recorder.get_recorded_actions()
            for action in actions:
                self.current_macro.add_action(action)
            self._refresh_action_list()
            self._log(f"{len(actions)}個のアクションを記録しました")
    
    def _on_action_recorded(self, action: MacroAction) -> None:
        """アクション記録時のコールバック"""
        self._refresh_action_list()
    
    def _on_tree_select(self, event) -> None:
        """ツリー選択時"""
        selection = self.project_tree.selection()
        if selection:
            item_id = selection[0]
            item_text = self.project_tree.item(item_id, 'text')
            # マクロ選択処理（簡易版）
            self._refresh_action_list()
    
    def _on_action_select(self, event) -> None:
        """アクション選択時"""
        selection = self.action_listbox.curselection()
        if selection and self.current_macro:
            index = selection[0]
            action = self.current_macro.actions[index]
            self._show_action_properties(action)
    
    def _undo(self) -> None:
        """元に戻す"""
        self._log("元に戻す (未実装)")
    
    def _redo(self) -> None:
        """やり直す"""
        self._log("やり直す (未実装)")
    
    def _open_settings(self) -> None:
        """設定を開く"""
        messagebox.showinfo("設定", "設定画面 (未実装)")
    
    def _show_about(self) -> None:
        """バージョン情報"""
        messagebox.showinfo("バージョン情報", "MacroMaker V2 v1.0.0\n高性能なGUIマクロソフト")
    
    # ===== ユーティリティメソッド =====
    
    def _refresh_tree(self) -> None:
        """プロジェクトツリーを更新"""
        self.project_tree.delete(*self.project_tree.get_children())
        if self.current_project:
            project_id = self.project_tree.insert("", tk.END, text=self.current_project.name)
            for macro in self.current_project.macros:
                self.project_tree.insert(project_id, tk.END, text=macro.name)
    
    def _refresh_action_list(self) -> None:
        """アクションリストを更新"""
        self.action_listbox.delete(0, tk.END)
        if self.current_macro:
            for i, action in enumerate(self.current_macro.actions):
                info = get_action_info(action.action_type)
                display_text = f"{i+1}. {info['icon']} {info['name']}"
                self.action_listbox.insert(tk.END, display_text)
    
    def _show_action_properties(self, action: MacroAction) -> None:
        """アクションのプロパティを表示"""
        self.property_text.delete(1.0, tk.END)
        info = get_action_info(action.action_type)
        
        text = f"アクション: {info['name']}\n"
        text += f"説明: {info['description']}\n"
        text += f"有効: {action.enabled}\n"
        text += f"\nパラメータ:\n"
        
        for param in action.parameters:
            text += f"  {param.name}: {param.value}\n"
        
        self.property_text.insert(1.0, text)
    
    def _log(self, message: str) -> None:
        """ログを出力"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        self.log_text.insert(tk.END, log_message)
        self.log_text.see(tk.END)
        logger.info(message)
    
    def run(self) -> None:
        """GUIを実行"""
        self._log("MacroMaker V2 起動")
        self.root.mainloop()
        
        # 終了時にウィンドウ位置を保存
        x = self.root.winfo_x()
        y = self.root.winfo_y()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        self.settings_manager.set_window_geometry(x, y, w, h)


# tkinter の simpledialog を追加でインポート
import tkinter.simpledialog as tk_simpledialog
