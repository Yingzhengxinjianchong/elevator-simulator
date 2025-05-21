# gui.elevator_ui.py
import gradio as gr
import threading
import time
from gui.elevator_state import state_manager
from request import Request, RequestType, UserIntent, Direction

NUM_ELEVATORS = 5
NUM_FLOORS = 20

button_refs = {
    "external": {},  # (floor, intent) -> button
    "internal": {},  # (eid, floor) -> button
}
status_htmls = {}  # eid -> gr.HTML()

CUSTOM_CSS = """
button.small-btn {
    width: 40px !important;
    height: 40px !important;
    font-size: 20px !important;
    padding: 2px 4px !important;
    margin: 2px !important;
    min-width: 45px !important;
    max-width: 45px !important;
    display: inline-block !important;
}
.big-btn {
    width: 40px !important;
    height: 40px !important;
    font-size: 20px !important;
    padding: 2px 4px !important;
    margin: 2px !important;
    min-width: 55px !important;
    max-width: 55px !important;
    display: inline-block !important;
}
.stop-btn {
    font-size: 20px !important;
    width: 100px !important;
    height: 35px !important;
    min-width: 150px !important;
    max-width: 150px !important;
    padding: 2px 4px !important;
    margin: 4px !important;
}
.status-box {
    font-size: 20px;
    padding: 4px;
}
"""

def create_ui(elevator_threads):
    stop_event = threading.Event()

    with gr.Blocks(title="电梯系统可视化", css=CUSTOM_CSS) as demo:
        gr.Markdown("# 🛗 多电梯调度系统")

        # 停止按钮
        with gr.Row():
            stop_button = gr.Button("🟥 停止程序", elem_classes="stop-btn")

            def stop_program():
                stop_event.set()
                with open("elevator_log.txt", "a", encoding="utf-8") as f:
                    f.write("🚨 用户终止了程序运行。\n")
                for elevator in elevator_threads:
                    elevator.stop()
                import os
                os._exit(0)

            stop_button.click(stop_program, None)

        with gr.Row():
            # 外部请求按钮
            with gr.Column(scale=1):
                gr.Markdown("## 楼梯间（外部请求）")
                floors = list(reversed(range(1, NUM_FLOORS + 1)))
                for i in range(0, len(floors), 2):
                    with gr.Row():
                        for floor in floors[i:i+2]:
                            for intent, symbol in [(UserIntent.UP, "🔼"), (UserIntent.DOWN, "🔽")]:
                                btn = gr.Button(f"{floor}{symbol}", elem_classes="big-btn")
                                button_refs["external"][(floor, intent)] = btn

                                def make_external_func(f=floor, i=intent):
                                    def _submit():
                                        req = Request(floor=f, request_type=RequestType.EXTERNAL, user_intent=i)
                                        state_manager.set_external_button(f, i, True)
                                        elevator_threads[3].add_request(req)  ####
                                        with open("elevator_log.txt", "a", encoding="utf-8") as logf:
                                            logf.write(f"[外部请求] 楼层 {f} {i.name} 请求\n")
                                    return _submit

                                btn.click(make_external_func(), None)

            # 内部按钮 + 状态栏
            with gr.Column(scale=4):
                for eid in range(1, NUM_ELEVATORS + 1):
                    with gr.Group():
                        gr.Markdown(f"## 🚪 电梯 {eid}")

                        with gr.Row():
                            status_htmls[eid] = gr.HTML(value="状态更新中...", elem_classes="status-box")

                        for row in range(2):
                            with gr.Row():
                                for col in range(10):
                                    floor_num = row * 10 + col + 1
                                    btn = gr.Button(str(floor_num), elem_classes="small-btn")
                                    button_refs["internal"][(eid, floor_num)] = btn

                                    def make_internal_func(e=eid, f=floor_num):
                                        def _submit(e=e, f=f):
                                            req = Request(floor=f, request_type=RequestType.INTERNAL)
                                            state_manager.set_internal_button(e, f, True)
                                            elevator_threads[e - 1].add_request(req)
                                            with open("elevator_log.txt", "a", encoding="utf-8") as logf:
                                                logf.write(f"[内部请求] 电梯 {e} 内部请求前往 {f} 楼\n")
                                        return _submit

                                    btn.click(make_internal_func(), None)

        # 新建一个状态组件用于定时刷新
        dummy_state = gr.State(value=0)  # 触发器，无实际用途

        def update_status(dummy_input):  # dummy_input 是 dummy_state 的值
            snapshot = state_manager.get_snapshot()

            for floor in range(1, NUM_FLOORS + 1):
                for intent in [UserIntent.UP, UserIntent.DOWN]:
                    btn = button_refs["external"][(floor, intent)]
                    active = snapshot["external_buttons"][floor][intent.value]
                    symbol = "↑" if intent == UserIntent.UP else "↓"
                    btn_text = f"{floor}{symbol}" + ("✅" if active else "")
                    try:
                        btn.update(value=btn_text)
                    except:
                        pass

            for eid in range(1, NUM_ELEVATORS + 1):
                state = snapshot["elevators"][eid]
                floor = state["floor"]
                dir_str = state["direction"].name
                door = "开" if state["door_open"] else "关"

                try:
                    status_htmls[eid]=f"<div>楼层：<b>{floor}</b> ｜ 方向：<b>{dir_str}</b> ｜ 门：<b>{door}</b></div>"
                except Exception as e:
                    print(f"Error updating button状态: {e}")

            return (dummy_input + 1,*[status_htmls[eid] for eid in range(1, NUM_ELEVATORS + 1)])  # 返回值作为 dummy_state 的新值，形成循环

        outputs = [dummy_state] + [status_htmls[eid] for eid in range(1, NUM_ELEVATORS + 1)]
        timer = gr.Timer(value=0.5, active=True, render=True)
        timer.tick(update_status, inputs=dummy_state, outputs=outputs)

    return demo