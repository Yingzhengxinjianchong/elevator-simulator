# dispatcher.py
import threading
from request import Request

class Dispatcher:
    def __init__(self):
        # 外部请求共享资源（临界资源）
        self.external_requests = []

        # 信号量（互斥 + 同步控制）
        self.read_count = 0         # 正在读的线程数
        self.write_count = 0        # 正在等待或进行写的线程数

        # 同步与互斥信号量
        self.r_mutex = threading.Lock()     # 保护 read_count 修改
        self.w_mutex = threading.Lock()     # 保护 write_count 修改
        self.read_try = threading.Semaphore(1)  # 写者优先策略入口：新读者先抢票需判断写者是否在等
        self.resource = threading.Semaphore(1)  # 控制对共享数据的访问权限

    # ========== 写者行为：添加外部请求 ==========
    def add_request(self, request: Request):
        """写者行为：向共享 external_requests 添加一个外部请求"""
        # 写者优先策略：修改 write_count，决定是否加锁 resource
        self.w_mutex.acquire()
        self.write_count += 1
        if self.write_count == 1:
            self.read_try.acquire()  # 阻止新读者进入
        self.w_mutex.release()

        # 写者进入资源区
        self.resource.acquire()
        # --- 临界区 ---
        duplicate = any(
            req.floor == request.floor and 
            req.request_type == request.request_type and 
            req.user_intent == request.user_intent
            for req in self.external_requests
        )
        if not duplicate:
            self.external_requests.append(request)
            print(f"[Dispatcher] 添加外部请求: {request}")
        # --- 临界区结束 ---
        self.resource.release()

        # 写者退出
        self.w_mutex.acquire()
        self.write_count -= 1
        if self.write_count == 0:
            self.read_try.release()  # 没有写者了，允许读者进入
        self.w_mutex.release()

    # ========== 读者行为：电梯读取共享请求 ==========
    def get_requests(self):
        """读者行为：返回外部请求的当前快照，电梯读取请求时调用"""
        # 写者优先控制：先尝试进入 read_try 信号量
        self.read_try.acquire()
        self.r_mutex.acquire()
        self.read_count += 1
        if self.read_count == 1:
            self.resource.acquire()  # 第一个读者锁定资源，防止写者进入
        self.r_mutex.release()
        self.read_try.release()

        # --- 临界区：读取共享数据 ---
        snapshot = list(self.external_requests)
        # --- 临界区结束 ---

        # 离开临界区
        self.r_mutex.acquire()
        self.read_count -= 1
        if self.read_count == 0:
            self.resource.release()  # 最后一个读者释放锁
        self.r_mutex.release()

        return snapshot

    # ========== 写者行为：移除完成的请求 ==========
    def remove_request(self, floor: int, elevator_id: int) -> bool:
        """写者行为：移除指定楼层的请求，如果成功则返回 True"""
        self.w_mutex.acquire()
        self.write_count += 1
        if self.write_count == 1:
            self.read_try.acquire()
        self.w_mutex.release()

        self.resource.acquire()
        # --- 临界区 ---
        initial_len = len(self.external_requests)
        self.external_requests = [
            req for req in self.external_requests if req.floor != floor
        ]
        removed = len(self.external_requests) < initial_len
        if removed:
            print(f"[Dispatcher] 电梯 {elevator_id} 移除并响应了楼层 {floor} 的外部请求")
        # --- 临界区结束 ---
        self.resource.release()

        self.w_mutex.acquire()
        self.write_count -= 1
        if self.write_count == 0:
            self.read_try.release()
        self.w_mutex.release()

        return removed  # 如果确实响应了外部请求，返回 True