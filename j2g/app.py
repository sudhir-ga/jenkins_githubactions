import os
import docker
import zipfile
from flask import Flask, request, render_template, send_file

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
        uploaded_files = request.files.getlist("jenkinsfiles")
        if not uploaded_files:
            return "No files uploaded.", 400

        yaml_files = []
        for file in uploaded_files:
            if file.filename == "":
                continue

            # Save the uploaded Jenkinsfile
            jenkinsfile_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
            file.save(jenkinsfile_path)

            # Generate a unique YAML output filename
            output_filename = f"{os.path.splitext(file.filename)[0]}-github-actions.yml"
            output_path = os.path.join(app.config["OUTPUT_FOLDER"], output_filename)

            try:
                # Run the Docker container for each file
                docker_client.containers.run(
                    "jenkins-to-github",  # Your Docker image name
                    f"{jenkinsfile_path} {output_path}",
                    volumes={
                        os.path.abspath("."): {"bind": "/app", "mode": "rw"}
                    },
                    remove=True
                )
                yaml_files.append(output_path)
            except Exception as e:
                return f"Error processing {file.filename}: {e}", 500

        # Create a ZIP file with all YAML outputs
        zip_path = "./outputs/github-actions-results.zip"
        with zipfile.ZipFile(zip_path, "w") as zipf:
            for yaml_file in yaml_files:
                zipf.write(yaml_file, os.path.basename(yaml_file))

        # Return the ZIP file as a download
        return send_file(zip_path, as_attachment=True)

    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)
