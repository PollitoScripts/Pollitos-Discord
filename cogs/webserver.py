from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return "Servidor web corriendo 🐣"

def run():
    app.run(host="0.0.0.0", port=8080)
