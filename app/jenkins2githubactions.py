import argparse
import re
import yaml


def parse_jenkinsfile(jenkinsfile_content):
    """Parse the Jenkinsfile for environment variables, secrets, tools, and stages."""
    env_vars = parse_environment(jenkinsfile_content)
    secrets = detect_secrets(env_vars)
    stages = re.findall(r"stage\(['\"](.*?)['\"]\)\s*\{(.*?)\}", jenkinsfile_content, re.DOTALL)
    tools = parse_tools(jenkinsfile_content)
    docker_steps = detect_docker_steps(jenkinsfile_content)
    workflow_jobs = {}

    for stage_name, stage_content in stages:
        post_actions = parse_post_actions(stage_content)
        when_condition = parse_when(stage_content)
        
        workflow_jobs[stage_name] = {
            "steps": parse_steps(stage_content, docker_steps),
            "post": post_actions,
            "when": when_condition
        }

    return env_vars, secrets, tools, workflow_jobs


def parse_environment(jenkinsfile_content):
    """Parse global environment variables."""
    env_block = re.findall(r"environment\s*\{(.*?)\}", jenkinsfile_content, re.DOTALL)
    env_vars = {}

    if env_block:
        vars = re.findall(r"(\w+)\s*=\s*['\"](.*?)['\"]", env_block[0])
        for var, value in vars:
            env_vars[var] = value

    return env_vars


def detect_secrets(env_vars):
    """Detect potential secrets in environment variables (e.g., passwords, keys)."""
    secrets = [var for var in env_vars if "KEY" in var or "SECRET" in var or "PASSWORD" in var]
    return secrets


def parse_tools(jenkinsfile_content):
    """Parse the tools block and determine required setup actions."""
    tools_block = re.findall(r"tools\s*\{(.*?)\}", jenkinsfile_content, re.DOTALL)
    tools = []

    if tools_block:
        if "nodejs" in tools_block[0].lower():
            tools.append("actions/setup-node@v3")
        if "jdk" in tools_block[0].lower() or "java" in tools_block[0].lower():
            tools.append("actions/setup-java@v3")
        if "python" in tools_block[0].lower():
            tools.append("actions/setup-python@v2")

    return tools


def detect_docker_steps(jenkinsfile_content):
    """Detect Docker-related commands and return a list of Docker steps."""
    docker_steps = re.findall(r"(docker build|docker push|docker run)\s+([^\n]+)", jenkinsfile_content)
    return [{"run": f"{cmd} {args.strip()}"} for cmd, args in docker_steps]


def parse_steps(stage_content, docker_steps):
    """Parse individual steps in a stage and include Docker steps if present."""
    steps = re.findall(r"(sh|echo|env)\s+['\"](.*?)['\"]", stage_content)
    job_steps = []

    for step_type, command in steps:
        if step_type == "sh":
            job_steps.append({"run": command})
        elif step_type == "echo":
            job_steps.append({"run": f"echo {command}"})

    # Add Docker steps at the end of each stage if detected
    job_steps.extend(docker_steps)
    return job_steps


def parse_post_actions(stage_content):
    """Parse post actions for success, failure, always, and changed conditions."""
    post_actions = re.findall(r"(success|failure|always|changed)\s*\{\s*(.*?)\s*\}", stage_content, re.DOTALL)
    actions = {}

    for condition, command in post_actions:
        actions[condition] = [{"run": f"echo {command.strip()}"}]

    return actions


def parse_when(stage_content):
    """Parse 'when' conditions for conditional execution."""
    when_condition = re.findall(r"when\s*\{\s*expression\s*\{(.*?)\}\s*\}", stage_content, re.DOTALL)
    return when_condition[0].strip() if when_condition else None


def generate_github_actions_yaml(env_vars, secrets, tools, jobs):
    """Generate GitHub Actions workflow with Docker support, secrets, and dynamic job generation."""
    workflow = {
        "name": "CI",
        "on": ["push", "pull_request"],
        "env": env_vars,
        "defaults": {
            "run": {
                "shell": "bash"
            }
        },
        "jobs": {}
    }

    for stage_name, stage_details in jobs.items():
        job_name = stage_name.lower().replace(" ", "_")
        job = {
            "steps": []
        }

        # Add tool setup steps
        for tool in tools:
            job["steps"].append({"uses": tool})

        # Add GitHub secrets for sensitive environment variables
        for secret in secrets:
            job["steps"].append({"run": f"echo Using secret: ${{ secrets.{secret} }}"})

        # Add steps and 'if' condition for when
        if stage_details.get("when"):
            job["if"] = stage_details["when"]

        job["steps"].extend(stage_details["steps"] if "steps" in stage_details else [])

        # Add Docker-specific steps if any
        if any("docker" in step["run"] for step in stage_details["steps"]):
            job["steps"].append({"run": "echo Docker step detected!"})

        # Add matrix strategy for advanced builds
        if "Test" in stage_name:
            job["strategy"] = {
                "matrix": {
                    "os": ["ubuntu-latest", "windows-latest"],
                    "node_version": ["12", "14", "16"]
                }
            }

        workflow["jobs"][job_name] = job

    # Move runs-on to the top of the workflow for all jobs
    for job in workflow["jobs"].values():
        job["runs-on"] = "ubuntu-latest"

    return yaml.dump(workflow, default_flow_style=False)


def main():
    parser = argparse.ArgumentParser(description="Convert Jenkinsfile to advanced GitHub Actions workflow with Docker and secrets.")
    parser.add_argument("jenkinsfile", help="Path to the Jenkinsfile")
    parser.add_argument("output", help="Path to save the GitHub Actions YAML file")

    args = parser.parse_args()

    try:
        with open(args.jenkinsfile, "r") as jf:
            jenkinsfile_content = jf.read()

        env_vars, secrets, tools, jobs = parse_jenkinsfile(jenkinsfile_content)
        github_actions_yaml = generate_github_actions_yaml(env_vars, secrets, tools, jobs)

        with open(args.output, "w") as gh_yaml:
            gh_yaml.write(github_actions_yaml)

        print(f"GitHub Actions workflow with Docker support and secrets has been saved to {args.output}")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
