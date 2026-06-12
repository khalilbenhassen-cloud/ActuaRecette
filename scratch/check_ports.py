import socket

for port in [8000, 8501]:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1.0)
    try:
        s.connect(('127.0.0.1', port))
        print(f"Port {port} is OPEN")
    except Exception as e:
        print(f"Port {port} is CLOSED: {e}")
    finally:
        s.close()
