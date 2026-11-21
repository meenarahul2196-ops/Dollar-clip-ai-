
import os
import uuid
import zipfile
import subprocess
from flask import Flask, request, send_file, render_template_string

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024

os.makedirs("uploads", exist_ok=True)
os.makedirs("outputs", exist_ok=True)

PAGE = """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Dollar Clip AI</title>
<style>
body{background:#101827;color:white;font-family:Arial;padding:20px}
.card{max-width:480px;margin:auto;background:#202c40;padding:22px;border-radius:18px}
h1{text-align:center;color:#38bdf8}
input,select,button{width:100%;padding:14px;margin:12px 0;
box-sizing:border-box;border-radius:9px;font-size:16px}
button{background:#0ea5e9;color:white;border:0;font-weight:bold}
</style>
</head>
<body>
<div class="card">
<h1>✂️ Dollar Clip AI</h1>
<p>Turn your video into short clips</p>
<form action="/create" method="POST" enctype="multipart/form-data">
<label>Upload your video</label>
<input type="file" name="video" accept="video/*" required>

<label>Number of clips</label>
<select name="count">
<option value="5">5 Clips</option>
<option value="10">10 Clips</option>
</select>

<label>Clip duration</label>
<select name="duration">
<option value="30">30 Seconds</option>
<option value="60">60 Seconds</option>
<option value="90">90 Seconds</option>
</select>

<label>Video size</label>
<select name="size">
<option value="9:16">9:16 Shorts/Reels</option>
<option value="16:9">16:9 YouTube</option>
<option value="1:1">1:1 Square</option>
</select>

<button type="submit">Generate Clips</button>
</form>
</div>
</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(PAGE)

@app.route("/health")
def health():
    return {"status": "online"}

@app.route("/create", methods=["POST"])
def create():
    video = request.files.get("video")
    count = request.form.get("count", "5")
    duration = request.form.get("duration", "30")
    size = request.form.get("size", "9:16")

    if not video or not video.filename:
        return "Please select a video", 400

    if count not in ["5", "10"] or duration not in ["30", "60", "90"]:
        return "Invalid selection", 400

    dimensions = {
        "9:16": (720, 1280),
        "16:9": (1280, 720),
        "1:1": (1080, 1080)
    }

    if size not in dimensions:
        return "Invalid video size", 400

    job = str(uuid.uuid4())
    source = f"uploads/{job}.mp4"
    folder = f"outputs/{job}"
    os.makedirs(folder, exist_ok=True)
    video.save(source)

    try:
        probe = subprocess.run([
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            source
        ], capture_output=True, text=True, check=True)

        total = float(probe.stdout.strip())
        clip_count = int(count)
        clip_duration = int(duration)

        if total < clip_count:
            return "Video is too short", 400

        w, h = dimensions[size]
        clips = []

        for i in range(clip_count):
            start = (total - clip_duration) * i / max(clip_count - 1, 1)
            length = min(clip_duration, total - start)
            output = f"{folder}/clip_{i+1}.mp4"

            subprocess.run([
                "ffmpeg", "-y", "-ss", str(start),
                "-i", source, "-t", str(length),
                "-vf", f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}",
                "-c:v", "libx264", "-preset", "ultrafast",
                "-c:a", "aac", "-movflags", "+faststart",
                output
            ], capture_output=True, check=True)

            clips.append(output)

        archive = f"outputs/{job}.zip"
        with zipfile.ZipFile(archive, "w") as z:
            for clip in clips:
                z.write(clip, os.path.basename(clip))

        return send_file(archive, as_attachment=True,
                         download_name="Dollar_Clips.zip")

    except Exception as e:
        return "Processing error: " + str(e), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

