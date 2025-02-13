import os
import docker
from flask import Flask, request, render_template, send_from_directory

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "./uploads"
app.config["OUTPUT_FOLDER"] = "./outputs"
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
os.makedirs(app.config["OUTPUT_FOLDER"], exist_ok=True)

# Initialize Docker client
docker_client = docker.from_env()

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # Handle file upload and YAML filename
        jenkinsfile = request.files["jenkinsfile"]
        yaml_filename = request.form["yaml_filename"]

        if jenkinsfile and yaml_filename:
            jenkinsfile_path = os.path.join(app.config["UPLOAD_FOLDER"], "Jenkinsfile")
            output_path = os.path.join(app.config["OUTPUT_FOLDER"], yaml_filename)

            # Save the uploaded Jenkinsfile
            jenkinsfile.save(jenkinsfile_path)

            try:
                # Run the Docker container
                docker_client.containers.run(
                    "jenkins-to-github",  # Your Docker image name
                    f"{jenkinsfile_path} {output_path}",
                    volumes={
                        os.path.abspath("."): {"bind": "/app", "mode": "rw"}
                    },
                    remove=True
                )
                return send_from_directory(app.config["OUTPUT_FOLDER"], yaml_filename, as_attachment=True)
            except Exception as e:
                return f"Error: {e}"

    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)
