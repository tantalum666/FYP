"""Local interactive shopping/travel rehearsal. Never a merchant or ticket issuer."""

from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading

STYLE = """body{font:18px system-ui;max-width:1050px;margin:35px auto;color:#20252b;background:#f7f8fa}
main{background:white;padding:30px;border-radius:18px}label{display:inline-block;margin:12px}
input,select,button{font:inherit;padding:10px;border:1px solid #abb2c0;border-radius:8px}
button{cursor:pointer;margin:8px;background:#f0f1ff}article{padding:16px;border:1px solid #ccc;margin:12px 0}
.notice{padding:12px;background:#fff3cc}.hidden{display:none}strong{color:#353a97}#summary{white-space:pre-line;padding:20px}
"""
SHOP = """<h1>FYP test shop</h1><p class=notice>Fictional products. No real orders or payment.</p>
<label>Search products <input id=search type=search></label><button id=find>Search</button>
<article><h2>Soft tissues · 6 boxes per pack</h2><p id=price></p>
<label>Quantity <input id=qty type=number min=1 max=10 value=1></label>
<button id=add>Add to cart</button><button id=cart>Open cart</button></article>
<section id=review class=hidden><h2>Review cart</h2><label>Discount code <input id=code></label>
<button id=apply>Apply code</button><button id=refresh>Refresh price</button>
<div id=summary role=status></div><button id=order>Place order</button></section>
<p>Shipping HKD12; free above HKD60 before discount. SAVE10 gives 10% off items.</p>
<script>
let state=JSON.parse(localStorage.getItem('fyp-cart')||'{"quantity":0,"unit":10.5,"discount":false}');
function show(){document.querySelector('#price').textContent='HKD '+state.unit.toFixed(2)+' per pack';
let sub=state.quantity*state.unit,shipping=sub>=60?0:12,total=sub*(state.discount ? 0.9 : 1)+shipping;
document.querySelector('#summary').textContent=`Quantity: ${state.quantity} packs\nItems: HKD ${sub.toFixed(2)}\nShipping: HKD ${shipping.toFixed(2)}\nDiscount: ${state.discount?'10%':'none'}\nTotal: HKD ${total.toFixed(2)}\nStatus: Cart prepared; not ordered`;
localStorage.setItem('fyp-cart',JSON.stringify(state));}
document.querySelector('#find').onclick=()=>document.querySelector('article').hidden=!/tissue|paper|纸/i.test(document.querySelector('#search').value);
document.querySelector('#add').onclick=()=>{state.quantity=Number(document.querySelector('#qty').value);show()};
document.querySelector('#cart').onclick=()=>{document.querySelector('#review').classList.remove('hidden');show()};
document.querySelector('#apply').onclick=()=>{state.discount=document.querySelector('#code').value==='SAVE10';show()};
document.querySelector('#refresh').onclick=()=>{state.unit=15.5;show()};
document.querySelector('#order').onclick=()=>fetch('/commit',{method:'POST',body:'fictional-order'});document.querySelector('#qty').value=state.quantity||1;show();
</script>"""
FLIGHTS = """<h1>FYP flight rehearsal</h1><p class=notice>Fictional flights. Nothing can be paid or ticketed here.</p>
<label>From <select id=from><option>HKG</option><option>SIN</option></select></label>
<label>To <select id=to><option>TYO</option><option>BKK</option></select></label>
<label>Departure date <input id=date type=date value=2026-11-20></label>
<label>Adults <input id=adults type=number min=1 max=4 value=1></label>
<label>Baggage <select id=bag><option value=0>None</option><option value=20>20 kg</option><option value=30>30 kg</option></select></label>
<button id=search>Search flights</button><section id=offers class=hidden>
<article><h2>Harbor Air</h2><p>Base HKD880 + fees120; 20kg bag costs180. 19:30 HKG → 00:15 Tokyo next day.</p><button id=harbor>View Harbor fare</button></article>
<article><h2>Pearl Air</h2><p>Base HKD950 + fees90; 20kg bag included. 19:30 HKG → 00:15 Tokyo next day.</p><button id=pearl>View Pearl fare</button></article></section>
<section id=review class=hidden><h2>Review itinerary</h2><div id=summary role=status></div><button id=confirm>Confirm booking</button></section>
<script>
let state=JSON.parse(localStorage.getItem('fyp-flight')||'null');
function show(which){let q=Number(document.querySelector('#adults').value),b=Number(document.querySelector('#bag').value),d=document.querySelector('#date').value;
let price=which==='Pearl'?1040+(b>20?150:0):1000+(b>=20?180:0)+(b>20?150:0);
let next=new Date(Date.parse(d+'T00:00:00Z')+86400000).toISOString().slice(0,10);
state={which,q,b,d,next,total:q*price};localStorage.setItem('fyp-flight',JSON.stringify(state));render()}
function render(){if(!state)return;document.querySelector('#review').classList.remove('hidden');document.querySelector('#summary').textContent=`Airline: ${state.which}\nHKG → TYO\nDeparture: ${state.d} 19:30 Asia/Hong_Kong\nArrival: ${state.next} 00:15 Asia/Tokyo\nAdults: ${state.q}\nBaggage: ${state.b} kg\nTotal including fees: HKD ${state.total.toFixed(2)}\nStatus: Prepared; not booked or ticketed`}
document.querySelector('#search').onclick=()=>document.querySelector('#offers').classList.remove('hidden');
document.querySelector('#harbor').onclick=()=>show('Harbor');document.querySelector('#pearl').onclick=()=>show('Pearl');
document.querySelector('#confirm').onclick=()=>fetch('/commit',{method:'POST',body:'fictional-booking'});
if(state){document.querySelector('#date').value=state.d;document.querySelector('#adults').value=state.q;document.querySelector('#bag').value=state.b}render();
</script>"""


@contextmanager
def demo_server(kind):
    counters = {"submissions": 0}
    body = (
        "<!doctype html><html lang=en><meta charset=utf-8><title>FYP browser rehearsal</title>"
        f"<style>{STYLE}</style><main>"
        + (SHOP if kind == "demo:shopping" else FLIGHTS)
        + "</main></html>"
    ).encode()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            counters["submissions"] += 1
            self.send_response(409)
            self.end_headers()

        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", counters
    finally:
        server.shutdown()
        server.server_close()
