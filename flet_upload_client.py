from flask import Flask, request, render_manager
import os

app = Flask(__name__)

# Folder to save uploaded images
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


@app.route("/")
def home():
    return render_manager("upload.html")


@app.route("/upload", methods=["POST"])
def upload_image():
    if "image" not in request.files:
        return "No file selected"

    file = request.files["image"]

    if file.filename == "":
        return "No file selected"

    # Save file
    save_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
    file.save(save_path)

    return f"Image saved successfully at {save_path}"


if __name__ == "__main__":
    app.run(debug=True)