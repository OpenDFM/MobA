import socket
import subprocess
import platform


class SocketUtil:

    # 8080端口负责与android端进行通信
    def __init__(self, host='localhost', port=8080):
        # 创建一个Socket对象
        self.host = socket.gethostname()
        self.port = port
        self.clear_port()  # 在初始化时清理端口
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.ip_address = socket.gethostbyname(host)

        # 绑定端口
        self.server_socket.bind((self.host, self.port))

        # 设置最大连接数，超过后排队
        self.server_socket.listen(5)

    def clear_port(self):
        system = platform.system()

        if system == "Linux":
            # 查找占用端口的进程
            result = subprocess.run(["netstat", "-tuln"], capture_output=True, text=True)
            for line in result.stdout.splitlines():
                if f":{self.port}" in line:
                    pid = line.strip().split()[-1]
                    # 终止进程
                    subprocess.run(["kill", "-9", pid],stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    print(f"Terminated process {pid} on port {self.port}")
                    break
            # else:
                # print("No process is using port 8080")

        elif system == "Windows":
            # 查找占用端口的进程
            result = subprocess.run(["netstat", "-ano"], capture_output=True, text=True)
            for line in result.stdout.splitlines():
                if f"{self.port}" in line:
                    pid = line.strip().split()[-1]
                    # 终止进程
                    subprocess.run(["taskkill", "/F", "/PID", pid], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    print(f"Terminated process {pid} on port {self.port}")
                    break
            # else:
            #     print("No process is using port 8080")

    def user_input(self):
        self.client_socket, addr = self.server_socket.accept()
        # print(f"连接地址: {addr}")

        # 接收数据
        data = self.client_socket.recv(1024).decode('utf-8')
        data = data.replace(" ", "")
        print(f"Task Input : {data}")
        return data

    def user_response(self, response):
        if hasattr(self, 'client_socket'):
            self.client_socket.send(response.encode('utf-8'))
        else:
            print("Error: No client is connected.")

    def user_close(self):
        if hasattr(self, 'client_socket'):
            self.client_socket.close()
        self.server_socket.close()

