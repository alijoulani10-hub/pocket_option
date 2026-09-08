from flask import Flask, jsonify
import os

app = Flask(__name__)


@app.route("/")
def home():
    return jsonify({
        "status": "ok",
        "message": "Pocket Option service is running"
    })


@app.route("/health")
def health():
    return jsonify({
        "status": "healthy"
    })


@app.route("/test")
def test():
    return "TEST OK"


@app.route("/config-check")
def config_check():
    return jsonify({
        "PO_SESSION": bool(os.environ.get("PO_SESSION")),
        "PO_UID": bool(os.environ.get("PO_UID")),
        "IS_DEMO": bool(os.environ.get("IS_DEMO"))
    })


@app.route("/library-check")
def library_check():
    try:
        import pocket_option

        return jsonify({
            "status": "ok",
            "library": "pocket_option loaded"
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
