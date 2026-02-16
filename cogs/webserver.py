from flask import Flask
import threading
import os

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot de Discord activo ✅"

def run():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

# Esto arranca Flask en un hilo paralelo para que tu bot también corra
threading.Thread(target=run).start()
