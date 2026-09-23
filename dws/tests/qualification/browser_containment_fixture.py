"""Synthetic dual-stack HTTP/TLS/DNS and independent TCP/UDP observers."""

from __future__ import annotations

import base64
import hashlib
import ipaddress
import json
import socket
import ssl
import struct
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

EVENTS: list[dict[str, Any]] = []
LOCK = threading.Lock()


def record(kind: str, **fields: Any) -> None:
    with LOCK:
        EVENTS.append({"kind": kind, **fields})


def address(value: str) -> str:
    ip = ipaddress.ip_address(value.split("%")[0])
    return str(ip.ipv4_mapped or ip) if isinstance(ip, ipaddress.IPv6Address) else str(ip)


def udp(family: int, port: int) -> None:
    sock = socket.socket(family, socket.SOCK_DGRAM)
    if family == socket.AF_INET6:
        sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
        sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_RECVPKTINFO, 1)
        sock.bind(("::", port))
    else:
        sock.setsockopt(socket.SOL_IP, 8, 1)
        sock.bind(("0.0.0.0", port))
    while True:
        data, ancillary, _, peer = sock.recvmsg(4096, 1024)
        for level, kind, value in ancillary:
            if level == socket.SOL_IP and kind == 8:
                destination = socket.inet_ntoa(value[8:12])
            elif level == socket.IPPROTO_IPV6 and kind == socket.IPV6_PKTINFO:
                destination = socket.inet_ntop(socket.AF_INET6, value[:16])
            else:
                continue
            record(
                "udp",
                destination=destination,
                port=port,
                peer=list(peer),
                bytes=len(data),
                prefix_hex=data[:64].hex(),
            )


def turn_tcp() -> None:
    sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
    sock.bind(("::", 3478))
    sock.listen(32)
    while True:
        client, peer = sock.accept()
        record("tcp", destination=address(client.getsockname()[0]), port=3478, peer=list(peer))
        client.settimeout(1)
        try:
            data = client.recv(4096)
            record(
                "turn_data",
                destination=address(client.getsockname()[0]),
                bytes=len(data),
                prefix_hex=data[:64].hex(),
            )
        except TimeoutError:
            pass
        finally:
            client.close()


def dns() -> None:
    config = json.loads(Path("/fixtures/dns.json").read_text())
    counts: dict[str, int] = {}
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", 53))
    while True:
        packet, peer = sock.recvfrom(4096)
        offset, labels = 12, []
        while packet[offset]:
            length = packet[offset]
            labels.append(packet[offset + 1 : offset + 1 + length].decode("ascii"))
            offset += length + 1
        kind = struct.unpack("!H", packet[offset + 1 : offset + 3])[0]
        name = ".".join(labels)
        candidates = config.get(name, [])
        if isinstance(candidates, dict):
            index = counts.get(name, 0)
            if kind == candidates["type"]:
                counts[name] = index + 1
            candidates = candidates["first"] if index == 0 else candidates["later"]
        addresses = [
            ip
            for ip in candidates
            if (":" in ip and kind == 28) or (":" not in ip and kind == 1)
        ]
        record("dns", name=name, type=kind, answers=addresses)
        response = packet[:2] + struct.pack("!HHHHH", 0x8180, 1, len(addresses), 0, 0)
        response += packet[12 : offset + 5]
        for ip in addresses:
            packed = ipaddress.ip_address(ip).packed
            response += b"\xc0\x0c" + struct.pack("!HHIH", kind, 1, 0, len(packed)) + packed
        sock.sendto(response, peer)


class Server(ThreadingHTTPServer):
    address_family = socket.AF_INET6
    daemon_threads = True
    tls: ssl.SSLContext | None = None

    def server_bind(self) -> None:
        self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        super().server_bind()

    def get_request(self) -> tuple[socket.socket, Any]:
        client, peer = self.socket.accept()
        client.settimeout(5)
        if self.server_port != 8081:
            record(
                "tcp",
                destination=address(client.getsockname()[0]),
                port=self.server_port,
                peer=list(peer),
            )
        if self.tls:
            try:
                client = self.tls.wrap_socket(client, server_side=True)
            except ssl.SSLError:
                client.close()
                raise
        return client, peer


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        pass

    def do_GET(self) -> None:
        parsed = urlsplit(self.path)
        if self.server.server_port == 8081:  # type: ignore[attr-defined]
            body = json.dumps(EVENTS).encode()
            mime = "application/json"
        else:
            record(
                "http",
                path=self.path,
                destination=address(self.connection.getsockname()[0]),
                port=self.connection.getsockname()[1],
            )
            target = parse_qs(parsed.query).get("to", [""])[0]
            if parsed.path == "/redirect":
                self.send_response(302)
                self.send_header("Location", target)
                self.end_headers()
                return
            if self.headers.get("Upgrade", "").lower() == "websocket":
                key = self.headers.get("Sec-WebSocket-Key", "")
                accept = base64.b64encode(
                    hashlib.sha1(
                        (key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()
                    ).digest()
                ).decode()
                self.send_response(101)
                self.send_header("Upgrade", "websocket")
                self.send_header("Connection", "Upgrade")
                self.send_header("Sec-WebSocket-Accept", accept)
                self.end_headers()
                self.wfile.write(b"\x81\x02ok")
                return
            mime = "text/html"
            if parsed.path == "/page":
                wt_target = parse_qs(parsed.query).get("wt", [""])[0]
                body = (
                    """<html><body><h1>DWS synthetic browser qualification</h1><p>
This substantial article tests real DOM rendering and transport policy.
All destinations are independent listeners in disposable isolated containers.
No credentials or real private services are involved. Independent counters distinguish
actual network activity from API errors and action markers are set after issuance.</p>
<p id="proof">not rendered</p><p id="ws"></p><p id="complete"></p>
<pre id="dws-state"></pre><script>
"""
                    + f"const t={json.dumps(target)}, wtTarget={json.dumps(wt_target)};"
                    + """
window.dwsState={actions:{},complete:false,webtransport:{issued:false,
constructed:false,error:null,ready:'not-issued'}};
const state=window.dwsState;
function publish(){document.getElementById('dws-state').textContent=JSON.stringify(state);}
function issue(name,fn){
  const action=state.actions[name]={issued:true,constructed:false,error:null};
  try{const value=fn();action.constructed=true;return value;}
  catch(e){action.error=String(e);return null;}
}
document.getElementById('proof').textContent='DWS_RENDERED_OK';
const pending=[];
if(t){
  issue('fetch',()=>fetch(t+'/fetch').catch(()=>{}));
  issue('beacon',()=>navigator.sendBeacon(t+'/beacon','test'));
  for(const tag of ['img','script','iframe']){
    issue(tag,()=>{const e=document.createElement(tag);e.src=t+'/'+tag;
      document.body.appendChild(e);return e;});
  }
  issue('ws',()=>{const ws=new WebSocket(t.replace(/^http/,'ws')+'/ws');
    ws.onopen=()=>document.getElementById('ws').textContent='DWS_WS_OPEN';return ws;});
  window.pcs=[];const h=new URL(t).hostname;
  for(const protocol of ['stun:','turn:']){
    const pc=issue(protocol,()=>new RTCPeerConnection({iceServers:[{
      urls:protocol+h+':3478'+(protocol==='turn:'?'?transport=tcp':''),
      username:'synthetic',credential:'synthetic'}]}));
    if(pc){pcs.push(pc);pc.createDataChannel('test');
      pending.push(pc.createOffer().then(o=>pc.setLocalDescription(o))
        .catch(e=>{state.actions[protocol].offer_error=String(e);}));}
  }
  state.webtransport.available=typeof WebTransport==='function';
  if(state.webtransport.available){
    const w=state.webtransport;w.issued=true;w.target=wtTarget||'https://'+h+':443/transport';
    try{window.wt=new WebTransport(w.target);w.constructed=true;w.ready='pending';
      wt.ready.then(()=>{w.ready='connected';publish();},
        e=>{w.ready='rejected';w.ready_error=String(e);publish();});
      wt.closed.catch(()=>{});
    }catch(e){w.error=String(e);}
  }
  Promise.allSettled(pending).then(()=>{
    state.complete=true;document.getElementById('complete').textContent='DWS_ACTIONS_ISSUED';
    publish();
  });
}
publish();
</script></body></html>"""
                ).encode()
            elif parsed.path.endswith("/img"):
                mime = "image/svg+xml"
                body = b'<svg xmlns="http://www.w3.org/2000/svg" width="2" height="2"/>'
            elif parsed.path.endswith("/script"):
                mime = "application/javascript"
                body = b"document.body.dataset.externalScript='loaded';"
            else:
                body = b"<p>DWS independent resource observer.</p>"
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        self.rfile.read(int(self.headers.get("Content-Length", "0")))
        self.do_GET()


def main() -> None:
    for family in (socket.AF_INET, socket.AF_INET6):
        for port in (3478, 443):
            threading.Thread(target=udp, args=(family, port), daemon=True).start()
    for target in (dns, turn_tcp):
        threading.Thread(target=target, daemon=True).start()
    for port in (8080, 8081, 8443, 8444):
        server = Server(("::", port), Handler)
        if port in (8443, 8444):
            server.tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            name = "server" if port == 8443 else "untrusted"
            server.tls.load_cert_chain(f"/fixtures/{name}.crt", f"/fixtures/{name}.key")
        threading.Thread(target=server.serve_forever, daemon=True).start()
    print("FIXTURE_READY", flush=True)
    threading.Event().wait()


if __name__ == "__main__":
    main()
