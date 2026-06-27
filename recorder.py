"""
MacroMaker V2 - Macro Recorder
マクロ記録機能（キーボード・マウス入力をキャプチャ）
"""

import threading
import time
import logging
from typing import List, Optional, Callable
from enum import Enum
from macro_actions import MacroAction, ActionFactory, ActionType

logger = logging.getLogger(__name__)


class RecorderState(Enum):
    """記録状態"""
    IDLE = "idle"              # アイドル状態
    RECORDING = "recording"    # 記録中
    PAUSED = "paused"          # 一時停止
    STOPPED = "stopped"        # 停止


class MacroRecorder:
    """マクロ記録エンジン"""
    
    def __init__(self,
                 on_action_recorded: Optional[Callable[[MacroAction], None]] = None,
                 on_state_change: Optional[Callable[[RecorderState], None]] = None,
                 on_log: Optional[Callable[[str], None]] = None):
        """
        初期化
        
        Args:
            on_action_recorded: アクション記録時のコールバック
            on_state_change: 状態変更時のコールバック
            on_log: ログ出力時のコールバック
        """
        self.on_action_recorded = on_action_recorded
        self.on_state_change = on_state_change
        self.on_log = on_log
        
        self.state = RecorderState.IDLE
        self.is_recording = False
        self.is_paused = False
        self.recorded_actions: List[MacroAction] = []
        
        self.last_action_time = time.time()
        self.listener_thread: Optional[threading.Thread] = None
        self.keyboard_listener = None
        self.mouse_listener = None
    
    def _set_state(self, new_state: RecorderState) -> None:
        """状態を変更"""
        if self.state != new_state:
            self.state = new_state
            logger.info(f"Recorder state changed: {new_state.value}")
            if self.on_state_change:
                self.on_state_change(new_state)
    
    def _log(self, message: str) -> None:
        """ログを出力"""
        logger.info(message)
        if self.on_log:
            self.on_log(message)
    
    def start(self) -> None:
        """記録を開始"""
        if self.is_recording:
            self._log("記録はすでに開始しています")
            return
        
        self.is_recording = True
        self.is_paused = False
        self.recorded_actions.clear()
        self.last_action_time = time.time()
        
        self._set_state(RecorderState.RECORDING)
        self._log("マクロ記録開始")
        
        # リスナーを開始
        self._start_listeners()
    
    def pause(self) -> None:
        """記録を一時停止"""
        if self.is_recording and not self.is_paused:
            self.is_paused = True
            self._set_state(RecorderState.PAUSED)
            self._log("記録を一時停止しました")
    
    def resume(self) -> None:
        """記録を再開"""
        if self.is_paused:
            self.is_paused = False
            self.last_action_time = time.time()
            self._set_state(RecorderState.RECORDING)
            self._log("記録を再開しました")
    
    def stop(self) -> None:
        """記録を停止"""
        self.is_recording = False
        self._set_state(RecorderState.STOPPED)
        self._stop_listeners()
        self._log(f"記録停止 ({len(self.recorded_actions)}個のアクション)")
    
    def get_recorded_actions(self) -> List[MacroAction]:
        """記録されたアクションを取得"""
        return self.recorded_actions.copy()
    
    def clear_actions(self) -> None:
        """記録されたアクションをクリア"""
        self.recorded_actions.clear()
        self._log("記録内容をクリアしました")
    
    def _start_listeners(self) -> None:
        """キーボード・マウスリスナーを開始"""
        try:
            from pynput import keyboard, mouse
            
            # キーボードリスナー
            def on_key_press(key):
                if not self.is_recording or self.is_paused:
                    return
                self._on_key_press(key)
            
            def on_key_release(key):
                if not self.is_recording or self.is_paused:
                    return
                self._on_key_release(key)
            
            # マウスリスナー
            def on_move(x, y):
                if not self.is_recording or self.is_paused:
                    return
                # マウス移動は現在サポートしていない
                pass
            
            def on_click(x, y, button, pressed):
                if not self.is_recording or self.is_paused:
                    return
                # マウスクリックは現在サポートしていない
                pass
            
            def on_scroll(x, y, dx, dy):
                if not self.is_recording or self.is_paused:
                    return
                # スクロールは現在サポートしていない
                pass
            
            # リスナー開始
            self.keyboard_listener = keyboard.Listener(
                on_press=on_key_press,
                on_release=on_key_release
            )
            self.keyboard_listener.start()
            
            self.mouse_listener = mouse.Listener(
                on_move=on_move,
                on_click=on_click,
                on_scroll=on_scroll
            )
            self.mouse_listener.start()
            
            self._log("リスナーを開始しました")
        
        except Exception as e:
            logger.error(f"Failed to start listeners: {e}")
            self._log(f"❌ リスナー開始エラー: {e}")
    
    def _stop_listeners(self) -> None:
        """リスナーを停止"""
        try:
            if self.keyboard_listener:
                self.keyboard_listener.stop()
            if self.mouse_listener:
                self.mouse_listener.stop()
            self._log("リスナーを停止しました")
        except Exception as e:
            logger.error(f"Failed to stop listeners: {e}")
    
    def _on_key_press(self, key) -> None:
        """キー押下時の処理"""
        try:
            from pynput.keyboard import Key
            
            # 記録停止キー（Esc）
            if key == Key.esc:
                self.stop()
                return
            
            # キー名を取得
            key_name = self._get_key_name(key)
            
            # 遅延時間を計算
            current_time = time.time()
            delay_ms = int((current_time - self.last_action_time) * 1000)
            self.last_action_time = current_time
            
            # 遅延が大きい場合は待機アクションを挿入
            if delay_ms > 100 and len(self.recorded_actions) > 0:
                wait_action = ActionFactory.create_wait(delay_ms)
                self.recorded_actions.append(wait_action)
                if self.on_action_recorded:
                    self.on_action_recorded(wait_action)
                self._log(f"待機記録: {delay_ms}ms")
            
            # キー入力アクションを記録
            key_input_action = ActionFactory.create_key_input(key_name)
            self.recorded_actions.append(key_input_action)
            if self.on_action_recorded:
                self.on_action_recorded(key_input_action)
            self._log(f"キー記録: {key_name}")
        
        except Exception as e:
            logger.error(f"Key press recording error: {e}")
    
    def _on_key_release(self, key) -> None:
        """キー解放時の処理（現在は未使用）"""
        pass
    
    def _get_key_name(self, key) -> str:
        """pynput のキーオブジェクトからキー名を取得"""
        try:
            from pynput.keyboard import Key
            
            # 特殊キーの処理
            special_keys = {
                Key.enter: "enter",
                Key.space: "space",
                Key.tab: "tab",
                Key.backspace: "backspace",
                Key.delete: "delete",
                Key.esc: "esc",
                Key.shift: "shift",
                Key.ctrl: "ctrl",
                Key.alt: "alt",
                Key.cmd: "cmd",
                Key.up: "up",
                Key.down: "down",
                Key.left: "left",
                Key.right: "right",
                Key.home: "home",
                Key.end: "end",
                Key.page_up: "page_up",
                Key.page_down: "page_down",
                Key.f1: "f1",
                Key.f2: "f2",
                Key.f3: "f3",
                Key.f4: "f4",
                Key.f5: "f5",
                Key.f6: "f6",
                Key.f7: "f7",
                Key.f8: "f8",
                Key.f9: "f9",
                Key.f10: "f10",
                Key.f11: "f11",
                Key.f12: "f12",
            }
            
            if key in special_keys:
                return special_keys[key]
            
            # 通常のキー
            if hasattr(key, 'char') and key.char:
                return key.char.lower()
            
            return str(key).lower()
        
        except Exception as e:
            logger.error(f"Key name parsing error: {e}")
            return "unknown"
    
    def get_status(self) -> dict:
        """記録状態を取得"""
        return {
            "state": self.state.value,
            "action_count": len(self.recorded_actions),
            "is_paused": self.is_paused,
        }
