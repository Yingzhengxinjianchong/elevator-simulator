# request.py
from enum import Enum
import time

class Direction(Enum): # of elevator
    UP = "UP"
    DOWN = "DOWN"
    NONE = "NONE"  # idled elevator

class RequestType(Enum):
    """
    参数说明：
    - INTERNAL: 用户在电梯内部按楼层按钮发出的请求
    - EXTERNAL: 用户在楼梯间按上/下按钮发出的请求
    """
    INTERNAL = "INTERNAL"
    EXTERNAL = "EXTERNAL"

class UserIntent(Enum):
    UP = "UP"
    DOWN = "DOWN"

class Request:
    def __init__(self, floor: int, request_type: RequestType, user_intent: UserIntent = None, timestamp: float = None):
        """
        参数说明：
        - floor: 请求涉及的楼层
        - request_type: INTERNAL or EXTERNAL
        - user_intent: 用户想上/下楼，仅 EXTERNAL 请求使用
        - timestamp: 请求产生的时间（默认当前时间）
        """
        self.floor = floor
        self.request_type = request_type
        self.user_intent = user_intent
        self.timestamp = timestamp if timestamp is not None else time.time()

    def __repr__(self):
        return (f"<Request floor={self.floor}, type={self.request_type.value}, "
                f"intent={self.user_intent.value if self.user_intent else 'N/A'}, "
                f"time={self.timestamp:.2f}>")