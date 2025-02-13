# Jenkinsfile to GitHub Actions Converter 🛠️🚀

Convert your Jenkinsfile to a GitHub Actions workflow YAML with ease using this Docker image!

## 📦 How to Use

1️⃣ **Run the Docker container with your Jenkinsfile:**

```bash
docker run --rm -v $(pwd):/app your-dockerhub-username/jenkins-to-github Jenkinsfile /app/github-actions.yml
