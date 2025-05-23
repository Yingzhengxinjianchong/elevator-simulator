#elevator.py
import time
import threading
from typing import List
from request import Direction, RequestType, Request
from dispatcher import Dispatcher
from gui.elevator_state import state_manager

class Elevator(threading.Thread):
    def __init__(self, elevator_id: int, dispatcher: Dispatcher):
        """
        参数说明：
        - elevator_id: 电梯号
        - current_floor: 电梯当前所在楼层
        - direction: 电梯运行方向
        - history_direction: 上一次电梯运行方向（与当前不同）
        - door_open: 电梯门是否打开
        - was_idle: 电梯是否空闲
        - internal_requests: 电梯的内部请求池
        - dispatcher: 传入的调度器实例
        - running: 电梯是否正在运行
        """
        super().__init__()
        self.elevator_id = elevator_id
        self.current_floor = 1
        self.direction = Direction.NONE
        self.history_direction = Direction.NONE
        self.door_open = False
        self.was_idle = False
        self.internal_requests: List[Request] = []
        self.dispatcher = dispatcher
        self.running = True

        # 初始状态推送
        state_manager.update_elevator(self.elevator_id, self.current_floor, self.direction, self.door_open)

    def add_request(self, request: Request):
        # 统一接口，区分内部和外部请求处理
        if request.request_type == RequestType.INTERNAL:
            if request.floor not in [r.floor for r in self.internal_requests]:
                self.internal_requests.append(request)
        elif request.request_type == RequestType.EXTERNAL:
            self.dispatcher.add_request(request)

    def run(self):
        while self.running:
            self.move()
            time.sleep(0.5)

    def stop(self):
        self.direction = Direction.NONE
        self.running = False
        state_manager.update_elevator(self.elevator_id, self.current_floor, self.direction, self.door_open)

    def sos(self):
        if self.running:
            self.stop()
            with open("elevator_log.txt", "a", encoding="utf-8") as logf:
                logf.write(f"[报警响应] 电梯 {self.elevator_id} 已停止运行\n")

    def remove_handled_requests(self, floor: int):
        self.internal_requests = [r for r in self.internal_requests if r.floor != floor]

        responded = self.dispatcher.remove_request(floor, self.elevator_id)
        if responded:
            with open("elevator_log.txt", "a", encoding="utf-8") as logf:
                logf.write(f"[电梯 {self.elevator_id}] 外部请求已响应于楼层 {floor}\n")
            #print(f"[电梯 {self.elevator_id}] 外部请求已响应于楼层 {floor}")

    def get_all_requests(self):
        external_requests = self.dispatcher.get_requests()
        return self.internal_requests + external_requests

    def has_pending_requests(self):
        return len(self.get_all_requests()) > 0

    def next_stop(self):
        if not self.has_pending_requests(): # 当前没有请求
            self.history_direction = self.direction # 记录历史方向
            self.direction = Direction.NONE # 置为空闲状态
            return None

        requests = self.get_all_requests()
        current_requests = [r for r in requests if r.floor == self.current_floor]
        if current_requests:
            return self.current_floor

        if self.direction == Direction.UP: # 当前是上行
            ups = [r for r in requests if r.floor > self.current_floor]
            if ups: # 楼上有请求
                return min(ups, key=lambda r: r.floor).floor # 去最近的楼
            downs = [r for r in requests if r.floor < self.current_floor]
            if downs: # 楼上没有，楼下有
                self.direction = Direction.DOWN # 改方向
                return max(downs, key=lambda r: r.floor).floor # 去最近的楼

        elif self.direction == Direction.DOWN:
            downs = [r for r in requests if r.floor < self.current_floor]
            if downs:
                return max(downs, key=lambda r: r.floor).floor
            ups = [r for r in requests if r.floor > self.current_floor]
            if ups:
                self.direction = Direction.UP
                return min(ups, key=lambda r: r.floor).floor

        elif self.direction == Direction.NONE:
            if self.history_direction == Direction.UP:
                ups = [r for r in requests if r.floor > self.current_floor]
                if ups:
                    self.direction = Direction.UP
                    return min(ups, key=lambda r: r.floor).floor
            elif self.history_direction == Direction.DOWN:
                downs = [r for r in requests if r.floor < self.current_floor]
                if downs:
                    self.direction = Direction.DOWN
                    return max(downs, key=lambda r: r.floor).floor

            earliest = min(requests, key=lambda r: r.timestamp)
            if earliest.floor > self.current_floor:
                self.direction = Direction.UP
                ups = [r for r in requests if r.floor > self.current_floor]
                return min(ups, key=lambda r: r.floor).floor
            elif earliest.floor < self.current_floor:
                self.direction = Direction.DOWN
                downs = [r for r in requests if r.floor < self.current_floor]
                return max(downs, key=lambda r: r.floor).floor
            else:
                self.direction = Direction.NONE
                return None

        return None

    def move(self):
        if not self.has_pending_requests():
            self.direction = Direction.NONE
            if not self.was_idle:
                with open("elevator_log.txt", "a", encoding="utf-8") as logf:
                    logf.write(f"[电梯 {self.elevator_id}] 空闲于 {self.current_floor} 层\n")
                #print(f"[电梯 {self.elevator_id}] 空闲于 {self.current_floor} 层")
                self.was_idle = True
                state_manager.update_elevator(self.elevator_id, self.current_floor, self.direction, self.door_open)
            return
        else:
            self.was_idle = False

        target_floor = self.next_stop()
        if target_floor is None:
            return

        if self.current_floor == target_floor:
            if not self.door_open:
                self.open_door()
            self.remove_handled_requests(self.current_floor)
            self.close_door()
            return

        if self.door_open:
            self.close_door()
        
        if self.current_floor < target_floor:
            self.current_floor += 1
        elif self.current_floor > target_floor:
            self.current_floor -= 1

        with open("elevator_log.txt", "a", encoding="utf-8") as logf:
            logf.write(f"[电梯 {self.elevator_id}] 正在移动至第 {self.current_floor} 层\n")
        #print(f"[电梯 {self.elevator_id}] 正在移动至第 {self.current_floor} 层")

        state_manager.update_elevator(self.elevator_id, self.current_floor, self.direction, self.door_open)
        time.sleep(1)

    def open_door(self):
        self.door_open = True
        with open("elevator_log.txt", "a", encoding="utf-8") as logf:
            logf.write(f"[电梯 {self.elevator_id}] 开门（楼层 {self.current_floor}）\n")
        #print(f"[电梯 {self.elevator_id}] 开门（楼层 {self.current_floor}）")
        state_manager.update_elevator(self.elevator_id, self.current_floor, self.direction, self.door_open)
        time.sleep(1.2)

    def close_door(self):
        with open("elevator_log.txt", "a", encoding="utf-8") as logf:
            logf.write(f"[电梯 {self.elevator_id}] 关门\n")
        #print(f"[电梯 {self.elevator_id}] 关门")
        time.sleep(1.2)
        self.door_open = False
        state_manager.update_elevator(self.elevator_id, self.current_floor, self.direction, self.door_open)