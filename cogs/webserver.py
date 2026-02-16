from flask import Flask
import threading

app = Flask(__name__)

@app.route("/")
def home():
    return "Servidor web corriendo 🐣"

def run():
    # Esto arranca Flask en un hilo separado
    app.run(host="0.0.0.0", port=8080)
