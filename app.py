
import os
import uuid
import zipfile
import subprocess
from flask import Flask, request, jsonify, send_file

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024

os.makedirs("uploads", exist_ok=True)
os.makedirs("outputs", exist_ok=True)

@app.route("/")
def home():
    return "Dollar Clip AI Engine is Running!"

@app.route("/health")
def health():
    return jsonify({"status": "online", "tool": "Dollar Clip AI"})

@app.route("/process", methods=["POST"])
def process():
    video = request.files.get("video")
    duration = request.form.get("duration", "30")
    size = request.form.get("size", "9:16")

    if not video:
        return jsonify({"error": "Please upload a video"}), 400

    if duration not in ["30", "60", "90"]:
        return jsonify({"error": "Invalid duration"}), 400

    if size not in ["9:16", "16:9", "1:1"]:
        return jsonify({"error": "Invalid video size"}), 400

    job = str(uuid.uuid4())
    source = f"uploads/{job}.mp4"
    folder = f"outputs/{job}"
    os.makedirs(folder, exist_ok=True)

    video.save(source)

    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries",
             "format=duration", "-of", "default=noprint_wrappers=1:nokey=1",
             source],
            capture_output=True, text=True, check=True
        )
        total = float(result.stdout.strip())

        w, h = {
            "9:16": (720, 1280),
            "16:9": (1280, 720),
            "1:1": (1080, 1080)
        }[size]

        count = 0
        start = 0

        while start < total:
            length = min(int(duration), total - start)
            if length < 1:
                break

            count += 1
            output = f"{folder}/clip_{count}.mp4"

            subprocess.run([
                "ffmpeg", "-y", "-ss", str(start),
                "-i", source, "-t", str(length),
                "-vf", f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}",
                "-c:v", "libx264", "-preset", "veryfast",
                "-c:a", "aac", "-movflags", "+faststart",
                output
            ], capture_output=True, check=True)

            start += int(duration)

        if count == 0:
            raise Exception("Video is too short")

        archive = f"outputs/{job}.zip"
        with zipfile.ZipFile(archive, "w") as z:
            for name in os.listdir(folder):
                z.write(f"{folder}/{name}", name)

        return send_file(
            archive, as_attachment=True,
            download_name="Dollar_Clip_AI.zip"
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
