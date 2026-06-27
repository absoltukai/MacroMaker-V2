"""
MacroMaker V2 - Macro Engine
マクロ実行エンジン（スタック構造対応）
"""

import threading
import time
import logging
from typing import List, Optional, Callable, Any
from enum import Enum
from macro_actions import MacroAction, ActionType

logger = logging.getLogger(__name__)


class ExecutionState(Enum):
    """実行状態"""
    IDLE = "idle"              # アイドル状態
    RUNNING = "running"        # 実行中
    PAUSED = "paused"          # 一時停止
    STOPPED = "stopped"        # 停止
    ERROR = "error"            # エラー


class LoopStackFrame:
    """ループスタックフレーム"""
    
    def __init__(self, start_line: int, loop_count: int):
        self.start_line = start_line           # ループ開始行
        self.loop_count = loop_count           # ループ回数（-1=無限）
        self.current_iteration = 0             # 現在のイテレーション
        self.loop_end_line: Optional[int] = None  # ループ終了行
    
    def increment(self) -> bool:
        """カウント増加。ループ終了ならTrue"""
        if self.loop_count == -1:  # 無限ループ
            self.current_iteration += 1
            return False
        
        self.current_iteration += 1
        return self.current_iteration >= self.loop_count
    
    def get_remaining_iterations(self) -> Optional[int]:
        """残りループ回数を取得（無限ループの場合はNone）"""
        if self.loop_count == -1:
            return None
        return self.loop_count - self.current_iteration


class MacroExecutor:
    """マクロ実行エンジン"""
    
    def __init__(self, 
                 actions: List[MacroAction],
                 on_action_start: Optional[Callable[[int, MacroAction], None]] = None,
                 on_action_end: Optional[Callable[[int, MacroAction], None]] = None,
                 on_state_change: Optional[Callable[[ExecutionState], None]] = None,
                 on_log: Optional[Callable[[str], None]] = None):
        """
        初期化
        
        Args:
            actions: 実行するアクションリスト
            on_action_start: アクション開始時のコールバック
            on_action_end: アクション終了時のコールバック
            on_state_change: 状態変更時のコールバック
            on_log: ログ出力時のコールバック
        """
        self.actions = actions
        self.on_action_start = on_action_start
        self.on_action_end = on_action_end
        self.on_state_change = on_state_change
        self.on_log = on_log
        
        self.state = ExecutionState.IDLE
        self.current_line = 0
        self.loop_stack: List[LoopStackFrame] = []
        self.is_running = False
        self.is_paused = False
        self.emergency_stop_count = 0
        self.execution_thread: Optional[threading.Thread] = None
    
    def _set_state(self, new_state: ExecutionState) -> None:
        """状態を変更"""
        if self.state != new_state:
            self.state = new_state
            logger.info(f"State changed: {new_state.value}")
            if self.on_state_change:
                self.on_state_change(new_state)
    
    def _log(self, message: str) -> None:
        """ログを出力"""
        logger.info(message)
        if self.on_log:
            self.on_log(message)
    
    def start(self) -> None:
        """マクロ実行を開始"""
        if self.is_running:
            self._log("マクロはすでに実行中です")
            return
        
        self.is_running = True
        self.is_paused = False
        self.emergency_stop_count = 0
        self.current_line = 0
        self.loop_stack.clear()
        
        self._set_state(ExecutionState.RUNNING)
        self._log("マクロ実行開始")
        
        # 別スレッドで実行
        self.execution_thread = threading.Thread(target=self._execute_loop, daemon=True)
        self.execution_thread.start()
    
    def pause(self) -> None:
        """マクロ実行を一時停止"""
        if self.is_running and not self.is_paused:
            self.is_paused = True
            self._set_state(ExecutionState.PAUSED)
            self._log("マクロ実行を一時停止しました")
    
    def resume(self) -> None:
        """マクロ実行を再開"""
        if self.is_paused:
            self.is_paused = False
            self._set_state(ExecutionState.RUNNING)
            self._log("マクロ実行を再開しました")
    
    def stop(self) -> None:
        """マクロ実行を停止"""
        self.is_running = False
        self._set_state(ExecutionState.STOPPED)
        self._log("マクロ実行を停止しました")
    
    def emergency_stop(self) -> None:
        """緊急停止（Esc 3回）"""
        self.emergency_stop_count += 1
        
        if self.emergency_stop_count >= 3:
            self.is_running = False
            self._set_state(ExecutionState.STOPPED)
            self._log("⚠️ 緊急停止されました")
            self.emergency_stop_count = 0
    
    def _execute_loop(self) -> None:
        """メイン実行ループ"""
        try:
            while self.is_running and self.current_line < len(self.actions):
                # 一時停止中なら待機
                while self.is_paused and self.is_running:
                    time.sleep(0.1)
                
                if not self.is_running:
                    break
                
                action = self.actions[self.current_line]
                
                # 無効化されているアクションはスキップ
                if not action.enabled:
                    self._log(f"[行{action.line_number}] スキップ（無効）")
                    self.current_line += 1
                    continue
                
                # アクション実行
                try:
                    success = self._execute_action(action)
                    if not success:
                        break
                except Exception as e:
                    self._log(f"❌ [行{action.line_number}] エラー: {e}")
                    self._set_state(ExecutionState.ERROR)
                    break
                
                self.current_line += 1
            
            if self.is_running:
                self._log("✅ マクロ実行完了")
            
            self.is_running = False
            self._set_state(ExecutionState.IDLE)
        
        except Exception as e:
            logger.error(f"Execution error: {e}", exc_info=True)
            self._log(f"❌ 実行エラー: {e}")
            self._set_state(ExecutionState.ERROR)
            self.is_running = False
    
    def _execute_action(self, action: MacroAction) -> bool:
        """単一のアクションを実行
        
        Returns:
            成功時True、停止指示時False
        """
        if self.on_action_start:
            self.on_action_start(action.line_number, action)
        
        try:
            action_type = action.action_type
            
            # キー押下
            if action_type == ActionType.KEY_PRESS:
                key = action.get_parameter("key").value
                self._log(f"[行{action.line_number}] キー押下: {key}")
                self._key_press(key)
            
            # キー解放
            elif action_type == ActionType.KEY_RELEASE:
                key = action.get_parameter("key").value
                self._log(f"[行{action.line_number}] キー解放: {key}")
                self._key_release(key)
            
            # キー入力
            elif action_type == ActionType.KEY_INPUT:
                key = action.get_parameter("key").value
                self._log(f"[行{action.line_number}] キー入力: {key}")
                self._key_input(key)
            
            # 文字列入力
            elif action_type == ActionType.TEXT_INPUT:
                text = action.get_parameter("text").value
                self._log(f"[行{action.line_number}] 文字列入力: {text}")
                self._text_input(text)
            
            # 待機
            elif action_type == ActionType.WAIT:
                duration_ms = action.get_parameter("duration_ms").value
                self._log(f"[行{action.line_number}] 待機: {duration_ms}ms")
                time.sleep(duration_ms / 1000)
            
            # ランダム待機
            elif action_type == ActionType.WAIT_RANDOM:
                min_ms = action.get_parameter("min_duration_ms").value
                max_ms = action.get_parameter("max_duration_ms").value
                import random
                wait_time = random.uniform(min_ms, max_ms) / 1000
                self._log(f"[行{action.line_number}] ランダム待機: {wait_time*1000:.0f}ms")
                time.sleep(wait_time)
            
            # ループ開始
            elif action_type == ActionType.LOOP_START:
                loop_count = action.get_parameter("loop_count").value
                frame = LoopStackFrame(action.line_number - 1, loop_count)
                self.loop_stack.append(frame)
                self._log(f"[行{action.line_number}] ループ開始: {loop_count}回")
            
            # ループ終了
            elif action_type == ActionType.LOOP_END:
                if not self.loop_stack:
                    self._log(f"❌ [行{action.line_number}] エラー: マッチするループ開始がありません")
                    return False
                
                frame = self.loop_stack[-1]
                frame.loop_end_line = action.line_number - 1
                
                if frame.increment():
                    # ループ終了
                    self.loop_stack.pop()
                    self._log(f"[行{action.line_number}] ループ終了")
                else:
                    # ループ継続
                    remaining = frame.get_remaining_iterations()
                    if remaining is None:
                        self._log(f"[行{action.line_number}] ループ継続 (無限ループ: {frame.current_iteration}回)")
                    else:
                        self._log(f"[行{action.line_number}] ループ継続 (残り{remaining}回)")
                    self.current_line = frame.start_line
                    return True
            
            # コメント
            elif action_type == ActionType.COMMENT:
                comment = action.get_parameter("comment_text").value or ""
                self._log(f"[行{action.line_number}] コメント: {comment}")
            
            # 停止
            elif action_type == ActionType.STOP:
                self._log(f"[行{action.line_number}] 停止命令")
                return False
            
            if self.on_action_end:
                self.on_action_end(action.line_number, action)
            
            return True
        
        except Exception as e:
            logger.error(f"Action execution error: {e}", exc_info=True)
            raise
    
    def _key_press(self, key: str) -> None:
        """キーを押す"""
        try:
            from pynput.keyboard import Controller, Key
            controller = Controller()
            
            # 特殊キーの処理
            special_keys = {
                'enter': Key.enter,
                'space': Key.space,
                'tab': Key.tab,
                'backspace': Key.backspace,
                'delete': Key.delete,
                'escape': Key.esc,
                'esc': Key.esc,
                'shift': Key.shift,
                'ctrl': Key.ctrl,
                'alt': Key.alt,
                'cmd': Key.cmd,
                'up': Key.up,
                'down': Key.down,
                'left': Key.left,
                'right': Key.right,
                'home': Key.home,
                'end': Key.end,
                'page_up': Key.page_up,
                'page_down': Key.page_down,
            }
            
            if key.lower() in special_keys:
                controller.press(special_keys[key.lower()])
            elif key.startswith('f') and key[1:].isdigit():
                # F1-F12
                func_key = getattr(Key, key, None)
                if func_key:
                    controller.press(func_key)
                else:
                    controller.press(key)
            else:
                controller.press(key)
        except Exception as e:
            logger.error(f"Key press error: {e}")
    
    def _key_release(self, key: str) -> None:
        """キーを離す"""
        try:
            from pynput.keyboard import Controller, Key
            controller = Controller()
            
            special_keys = {
                'enter': Key.enter,
                'space': Key.space,
                'tab': Key.tab,
                'backspace': Key.backspace,
                'delete': Key.delete,
                'escape': Key.esc,
                'esc': Key.esc,
                'shift': Key.shift,
                'ctrl': Key.ctrl,
                'alt': Key.alt,
                'cmd': Key.cmd,
                'up': Key.up,
                'down': Key.down,
                'left': Key.left,
                'right': Key.right,
                'home': Key.home,
                'end': Key.end,
                'page_up': Key.page_up,
                'page_down': Key.page_down,
            }
            
            if key.lower() in special_keys:
                controller.release(special_keys[key.lower()])
            elif key.startswith('f') and key[1:].isdigit():
                func_key = getattr(Key, key, None)
                if func_key:
                    controller.release(func_key)
                else:
                    controller.release(key)
            else:
                controller.release(key)
        except Exception as e:
            logger.error(f"Key release error: {e}")
    
    def _key_input(self, key: str) -> None:
        """キーを入力（押して離す）"""
        self._key_press(key)
        time.sleep(0.05)
        self._key_release(key)
    
    def _text_input(self, text: str) -> None:
        """テキストを入力"""
        try:
            from pynput.keyboard import Controller
            controller = Controller()
            controller.type(text)
        except Exception as e:
            logger.error(f"Text input error: {e}")
    
    def get_status(self) -> dict:
        """実行状態を取得"""
        loop_info = []
        for i, frame in enumerate(self.loop_stack):
            loop_info.append({
                "depth": i,
                "start_line": frame.start_line,
                "current_iteration": frame.current_iteration,
                "total_iterations": frame.loop_count,
                "remaining": frame.get_remaining_iterations(),
            })
        
        return {
            "state": self.state.value,
            "current_line": self.current_line,
            "total_lines": len(self.actions),
            "loop_stack": loop_info,
            "loop_depth": len(self.loop_stack),
        }
