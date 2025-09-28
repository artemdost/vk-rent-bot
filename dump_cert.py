import socket, ssl
from datetime import datetime
import os

HOSTS = ["api.vk.com", "api.vk.ru"]
OUT_DIR = r"C:\temp"
os.makedirs(OUT_DIR, exist_ok=True)

def save_peer_cert(host, port=443):
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        sock = socket.create_connection((host, port), timeout=10)
        ss = ctx.wrap_socket(sock, server_hostname=host)
        der = ss.getpeercert(binary_form=True)
        if not der:
            print(f"[{host}] No peer cert received.")
            return None
        pem = ssl.DER_cert_to_PEM_cert(der)
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        fname = os.path.join(OUT_DIR, f"{host.replace('.', '_')}_cert_{ts}.pem")
        with open(fname, "w", encoding="utf-8") as f:
            f.write(pem)
        print(f"[{host}] Saved cert to: {fname}")
        return fname
    except Exception as e:
        print(f"[{host}] Error: {e!r}")
    finally:
        try:
            ss.close()
        except:
            pass

if __name__ == "__main__":
    for h in HOSTS:
        save_peer_cert(h)
