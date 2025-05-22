# gui.elevator_ui.py
import gradio as gr
import threading
import time
from gui.elevator_state import state_manager
from request import Request, RequestType, UserIntent, Direction

NUM_ELEVATORS = 5
NUM_FLOORS = 20

button_refs = {
    "external": {},  # (eid, floor, intent) -> button
    "internal": {},  # (eid, floor) -> button
    "sos": {},       # (eid) -> button
    "open": {},      # (eid) -> button
    "close": {},     # (eid) -> button
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
.external-btn {
    width: 40px !important;
    height: 35px !important;
    font-size: 15px !important;
    padding: 0px 4px !important;
    margin: 0px !important;
    min-width: 40px !important;
    max-width: 40px !important;
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
                
                for floor in reversed(range(1, NUM_FLOORS + 1)):
                    gr.Markdown(f"### 🏢 {floor} F")

                    # 上行按钮行
                    with gr.Row():
                        for eid in range(1, NUM_ELEVATORS + 1):
                            label = f"E{eid}🔼"
                            btn = gr.Button(label, elem_classes=f"external-btn elevator-{eid}")
                            button_refs["external"][(eid, floor, UserIntent.UP)] = btn

                            def make_func(e=eid, f=floor, i=UserIntent.UP):
                                def _submit():
                                    req = Request(floor=f, request_type=RequestType.EXTERNAL, user_intent=i)
                                    state_manager.set_external_button(f, i, True)
                                    elevator_threads[e - 1].add_request(req)
                                    with open("elevator_log.txt", "a", encoding="utf-8") as logf:
                                        logf.write(f"[外部请求] {f} 楼用户上行，呼叫电梯 {e} \n")
                                return _submit

                            btn.click(make_func(), None)

                    # 下行按钮行
                    with gr.Row():
                        for eid in range(1, NUM_ELEVATORS + 1):
                            label = f"E{eid}🔽"
                            btn = gr.Button(label, elem_classes=f"external-btn elevator-{eid}")
                            button_refs["external"][(eid, floor, UserIntent.DOWN)] = btn

                            def make_func(e=eid, f=floor, i=UserIntent.DOWN):
                                def _submit():
                                    req = Request(floor=f, request_type=RequestType.EXTERNAL, user_intent=i)
                                    state_manager.set_external_button(f, i, True)
                                    elevator_threads[e - 1].add_request(req)
                                    with open("elevator_log.txt", "a", encoding="utf-8") as logf:
                                        logf.write(f"[外部请求] {f} 楼用户下行，呼叫电梯 {e} \n")
                                return _submit

                            btn.click(make_func(), None)


            # 内部按钮 + 状态栏
            with gr.Column(scale=4):
                for eid in range(1, NUM_ELEVATORS + 1):
                    with gr.Group():
                        gr.Markdown(f"## 🚪 电梯 {eid}")

                        with gr.Row():
                            status_htmls[eid] = gr.HTML(value="状态更新中...", elem_classes="status-box")
                            snapshot = state_manager.get_snapshot()

                            sos_event = threading.Event()
                            sos_btn = gr.Button("🔴 报警", elem_classes="stop-btn")
                            button_refs["sos"][eid] = sos_btn

                            def make_sos_func(e=eid):
                                sos_event.set()
                                def _stop(e=e):
                                    elevator_threads[e-1].stop()
                                    with open("elevator_log.txt", "a", encoding="utf-8") as logf:
                                        logf.write(f"[报警] 电梯 {e} 已停止运行\n")
                                    #print(f"电梯 {e} 报警")
                                return _stop
                            sos_btn.click(make_sos_func(), None)

                            open_event = threading.Event()
                            open_btn = gr.Button("开", elem_classes="small-btn")
                            button_refs["open"][eid] = open_btn

                            def make_open_func(e=eid):
                                open_event.set()
                                def _open(e=e):
                                    if not snapshot["elevators"][eid]["door_open"]:
                                        with open("elevator_log.txt", "a", encoding="utf-8") as logf:
                                            logf.write(f"[内部请求] 电梯 {e} 开门\n")
                                        elevator_threads[e-1].open_door()
                                    else:
                                        with open("elevator_log.txt", "a", encoding="utf-8") as logf:
                                            logf.write(f"[内部请求] 电梯 {e} 开门\n[拦截回应] 电梯 {e} 已开门\n")
                                return _open
                            open_btn.click(make_open_func(), None)

                            close_event = threading.Event()
                            close_btn = gr.Button("关", elem_classes="small-btn")
                            button_refs["close"][eid] = close_btn

                            def make_close_func(e=eid):
                                close_event.set()
                                def _close(e=e):
                                    if snapshot["elevators"][eid]["door_open"]:
                                        with open("elevator_log.txt", "a", encoding="utf-8") as logf:
                                            logf.write(f"[内部请求] 电梯 {e} 关门\n")
                                        elevator_threads[e-1].close_door()
                                    else:
                                        with open("elevator_log.txt", "a", encoding="utf-8") as logf:
                                            logf.write(f"[内部请求] 电梯 {e} 关门\n[拦截回应] 电梯 {e} 已关门\n")
                                return _close
                            close_btn.click(make_close_func(), None)

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