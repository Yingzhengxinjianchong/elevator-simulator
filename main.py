# main.py
import threading
import time
from dispatcher import Dispatcher
from elevator import Elevator
from gui.elevator_state import state_manager
from gui.elevator_ui import create_ui  # UI 构建函数

NUM_ELEVATORS = 5
NUM_FLOORS = 20

def main():
    # 初始化 Dispatcher 和 Elevator
    dispatcher = Dispatcher()
    elevators = [Elevator(i + 1, dispatcher) for i in range(NUM_ELEVATORS)]

    # 启动电梯线程
    for e in elevators:
        e.start()

    # 创建并启动 Gradio UI，把 elevators 传入 UI
    ui = create_ui(elevators)

    try:
        ui.launch()
    finally:
        # UI 关闭后安全关闭 Elevator 线程
        for e in elevators:
            e.stop()  # 请确保 Elevator 类有 stop() 方法设置退出标志位
        for e in elevators:
            e.join()  # 等待所有线程结束

if __name__ == "__main__":
    main()