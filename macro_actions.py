"""
MacroMaker V2 - Macro Actions Definition
マクロ命令の定義
"""

import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, List, Optional, Callable

logger = logging.getLogger(__name__)


class ActionType(Enum):
    """アクション（命令）のタイプ"""
    # キーボード関係
    KEY_PRESS = "key_press"           # キー押下
    KEY_RELEASE = "key_release"       # キー解放
    KEY_INPUT = "key_input"           # キー入力（押して離す）
    TEXT_INPUT = "text_input"         # 文字列入力
    
    # 待機
    WAIT = "wait"                     # 指定時間待つ
    WAIT_RANDOM = "wait_random"       # ランダム時間待つ
    
    # 制御
    LOOP_START = "loop_start"         # 繰り返し開始
    LOOP_END = "loop_end"             # 繰り返し終了
    COMMENT = "comment"               # コメント
    DISABLE = "disable"               # 無効化
    STOP = "stop"                     # 停止
    
    # 将来対応
    IF = "if"                         # 条件分岐
    ELSE = "else"                     # ELSE
    WHILE = "while"                   # WHILE
    VARIABLE_SET = "variable_set"     # 変数設定
    VARIABLE_GET = "variable_get"     # 変数取得


@dataclass
class ActionParameter:
    """アクションのパラメータ"""
    name: str                          # パラメータ名
    value: Any = None                  # パラメータ値
    param_type: str = "string"         # パラメータ型 (string, int, float, bool, choice)
    required: bool = True              # 必須かどうか
    description: str = ""              # 説明
    choices: List[str] = field(default_factory=list)  # 選択肢（param_type="choice"の場合）
    
    def validate(self) -> tuple[bool, str]:
        """パラメータの妥当性をチェック
        
        Returns:
            (valid: bool, message: str)
        """
        if self.required and self.value is None:
            return False, f"パラメータ '{self.name}' は必須です"
        
        if self.value is None:
            return True, ""
        
        try:
            if self.param_type == "int":
                if not isinstance(self.value, int):
                    int(self.value)
            elif self.param_type == "float":
                if not isinstance(self.value, float):
                    float(self.value)
            elif self.param_type == "choice":
                if self.value not in self.choices:
                    return False, f"パラメータ '{self.name}' の値が無効です: {self.value}"
            
            return True, ""
        except (ValueError, TypeError) as e:
            return False, f"パラメータ '{self.name}' の型が無効です: {e}"


@dataclass
class MacroAction:
    """マクロアクション（1つの命令）"""
    action_type: ActionType
    line_number: int = 0               # シーケンス内の行番号
    parameters: List[ActionParameter] = field(default_factory=list)
    enabled: bool = True               # 実行するかどうか
    comment: str = ""                  # コメント
    
    def validate(self) -> tuple[bool, str]:
        """アクションの妥当性をチェック
        
        Returns:
            (valid: bool, message: str)
        """
        for param in self.parameters:
            valid, msg = param.validate()
            if not valid:
                return False, msg
        return True, ""
    
    def get_parameter(self, name: str) -> Optional[ActionParameter]:
        """パラメータを名前で取得"""
        for param in self.parameters:
            if param.name == name:
                return param
        return None
    
    def set_parameter_value(self, name: str, value: Any) -> bool:
        """パラメータの値を設定"""
        param = self.get_parameter(name)
        if param:
            param.value = value
            return True
        return False
    
    def to_dict(self) -> dict:
        """辞書に変換"""
        return {
            "action_type": self.action_type.value,
            "line_number": self.line_number,
            "enabled": self.enabled,
            "comment": self.comment,
            "parameters": [
                {
                    "name": p.name,
                    "value": p.value,
                    "param_type": p.param_type,
                }
                for p in self.parameters
            ]
        }


class ActionFactory:
    """マクロアクション生成ファクトリ"""
    
    # キーボードキー一覧
    AVAILABLE_KEYS = [
        'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm',
        'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z',
        '0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
        'enter', 'space', 'tab', 'backspace', 'delete', 'escape', 'esc',
        'shift', 'ctrl', 'alt', 'cmd',
        'up', 'down', 'left', 'right',
        'home', 'end', 'page_up', 'page_down',
        'f1', 'f2', 'f3', 'f4', 'f5', 'f6', 'f7', 'f8', 'f9', 'f10', 'f11', 'f12',
    ]
    
    @staticmethod
    def create_key_press(key: str) -> MacroAction:
        """キー押下アクションを作成"""
        action = MacroAction(action_type=ActionType.KEY_PRESS)
        action.parameters.append(
            ActionParameter(
                name="key",
                value=key,
                param_type="choice",
                required=True,
                description="押すキー",
                choices=ActionFactory.AVAILABLE_KEYS
            )
        )
        return action
    
    @staticmethod
    def create_key_release(key: str) -> MacroAction:
        """キー解放アクションを作成"""
        action = MacroAction(action_type=ActionType.KEY_RELEASE)
        action.parameters.append(
            ActionParameter(
                name="key",
                value=key,
                param_type="choice",
                required=True,
                description="離すキー",
                choices=ActionFactory.AVAILABLE_KEYS
            )
        )
        return action
    
    @staticmethod
    def create_key_input(key: str) -> MacroAction:
        """キー入力アクション（押して離す）を作成"""
        action = MacroAction(action_type=ActionType.KEY_INPUT)
        action.parameters.append(
            ActionParameter(
                name="key",
                value=key,
                param_type="choice",
                required=True,
                description="入力するキー",
                choices=ActionFactory.AVAILABLE_KEYS
            )
        )
        return action
    
    @staticmethod
    def create_text_input(text: str) -> MacroAction:
        """文字列入力アクションを作成"""
        action = MacroAction(action_type=ActionType.TEXT_INPUT)
        action.parameters.append(
            ActionParameter(
                name="text",
                value=text,
                param_type="string",
                required=True,
                description="入力する文字列"
            )
        )
        return action
    
    @staticmethod
    def create_wait(milliseconds: int) -> MacroAction:
        """待機アクションを作成"""
        action = MacroAction(action_type=ActionType.WAIT)
        action.parameters.append(
            ActionParameter(
                name="duration_ms",
                value=milliseconds,
                param_type="int",
                required=True,
                description="待機時間（ミリ秒）"
            )
        )
        return action
    
    @staticmethod
    def create_wait_random(min_ms: int, max_ms: int) -> MacroAction:
        """ランダム待機アクションを作成"""
        action = MacroAction(action_type=ActionType.WAIT_RANDOM)
        action.parameters.extend([
            ActionParameter(
                name="min_duration_ms",
                value=min_ms,
                param_type="int",
                required=True,
                description="最小待機時間（ミリ秒）"
            ),
            ActionParameter(
                name="max_duration_ms",
                value=max_ms,
                param_type="int",
                required=True,
                description="最大待機時間（ミリ秒）"
            )
        ])
        return action
    
    @staticmethod
    def create_loop_start(loop_count: int) -> MacroAction:
        """繰り返し開始アクションを作成"""
        action = MacroAction(action_type=ActionType.LOOP_START)
        action.parameters.append(
            ActionParameter(
                name="loop_count",
                value=loop_count,
                param_type="int",
                required=True,
                description="繰り返し回数（-1=無限）"
            )
        )
        return action
    
    @staticmethod
    def create_loop_end() -> MacroAction:
        """繰り返し終了アクションを作成"""
        return MacroAction(action_type=ActionType.LOOP_END)
    
    @staticmethod
    def create_comment(text: str) -> MacroAction:
        """コメントアクションを作成"""
        action = MacroAction(action_type=ActionType.COMMENT)
        action.parameters.append(
            ActionParameter(
                name="comment_text",
                value=text,
                param_type="string",
                required=False,
                description="コメント内容"
            )
        )
        return action
    
    @staticmethod
    def create_stop() -> MacroAction:
        """停止アクションを作成"""
        return MacroAction(action_type=ActionType.STOP)
    
    @staticmethod
    def create_from_dict(data: dict) -> MacroAction:
        """辞書からアクションを生成"""
        action_type = ActionType(data["action_type"])
        action = MacroAction(
            action_type=action_type,
            line_number=data.get("line_number", 0),
            enabled=data.get("enabled", True),
            comment=data.get("comment", "")
        )
        
        for param_data in data.get("parameters", []):
            param = ActionParameter(
                name=param_data["name"],
                value=param_data["value"],
                param_type=param_data.get("param_type", "string"),
                required=param_data.get("required", True)
            )
            action.parameters.append(param)
        
        return action


def get_action_info(action_type: ActionType) -> dict:
    """アクションタイプの情報を取得"""
    info_map = {
        ActionType.KEY_PRESS: {
            "name": "キー押下",
            "description": "指定したキーを押し続ける",
            "icon": "🔽",
        },
        ActionType.KEY_RELEASE: {
            "name": "キー解放",
            "description": "押していたキーを離す",
            "icon": "🔼",
        },
        ActionType.KEY_INPUT: {
            "name": "キー入力",
            "description": "キーを押して離す",
            "icon": "⌨️",
        },
        ActionType.TEXT_INPUT: {
            "name": "文字列入力",
            "description": "テキストを入力する",
            "icon": "📝",
        },
        ActionType.WAIT: {
            "name": "待機",
            "description": "指定時間待つ",
            "icon": "⏱️",
        },
        ActionType.WAIT_RANDOM: {
            "name": "ランダム待機",
            "description": "ランダムな時間待つ",
            "icon": "🎲",
        },
        ActionType.LOOP_START: {
            "name": "繰り返し開始",
            "description": "繰り返しブロックを開始",
            "icon": "🔁",
        },
        ActionType.LOOP_END: {
            "name": "繰り返し終了",
            "description": "繰り返しブロックを終了",
            "icon": "🔚",
        },
        ActionType.COMMENT: {
            "name": "コメント",
            "description": "注釈を追加",
            "icon": "💬",
        },
        ActionType.DISABLE: {
            "name": "無効化",
            "description": "このアクションを実行しない",
            "icon": "❌",
        },
        ActionType.STOP: {
            "name": "停止",
            "description": "マクロ実行を停止",
            "icon": "⏹️",
        },
    }
    
    return info_map.get(action_type, {
        "name": "不明",
        "description": "未定義のアクション",
        "icon": "❓",
    })
