from flask import Flask, jsonify
import os
import asyncio

from pocket_option import PocketOptionClient
from pocket_option.constants import Regions
from pocket_option.contrib.default_init import default_init
from pocket_option.models import AuthorizationData

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


async def pocket_connection_test():
    client = PocketOptionClient(logger=False)

    is_demo = int(os.environ.get("IS_DEMO", "1"))

    default_init(
        client,
        authorization=AuthorizationData.model_validate({
            "session": os.environ["PO_SESSION"],
            "isDemo": is_demo,
            "uid": int(os.environ["PO_UID"]),
            "platform": 2,
            "isFastHistory": True,
            "isOptimized": True
        }),
        sub_assets=[],
        sub_period=30
    )

    connect_task = asyncio.create_task(
        client.connect(Regions.DEMO)
    )

    try:
        await asyncio.wait_for(
            client.authorized_event.wait(),
            timeout=15
        )

        return {
            "status": "ok",
            "connected": True,
            "authorized": True,
            "mode": "DEMO"
        }

    finally:
        try:
            await client.disconnect()
        except Exception:
            pass

        if not connect_task.done():
            connect_task.cancel()


@app.route("/connection-check")
def connection_check():
    try:
        result = asyncio.run(pocket_connection_test())
        return jsonify(result)

    except asyncio.TimeoutError:
        return jsonify({
            "status": "error",
            "connected": False,
            "authorized": False,
            "message": "Authorization timeout"
        }), 504

    except Exception as e:
        return jsonify({
            "status": "error",
            "connected": False,
            "authorized": False,
            "error": str(e)
        }), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
