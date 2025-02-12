import argparse
import re
import yaml


def parse_jenkinsfile(jenkinsfile_content):
    """Parse the Jenkinsfile and extract stages, including post actions and parallel stages."""
    stages = re.findall(r"stage\(['\"](.*?)['\"]\)\s*\{(.*?)\}", jenkinsfile_content, re.DOTALL)
    workflow_jobs = {}

    for stage_name, stage_content in stages:
        post_actions = parse_post_actions(stage_content)
        if "parallel" in stage_content:
            workflow_jobs[stage_name] = {
                "parallel": parse_parallel_stages(stage_content),
                "post": post_actions
            }
        else:
            workflow_jobs[stage_name] = {
                "steps": parse_steps(stage_content),
                "post": post_actions
            }

    return workflow_jobs


def parse_parallel_stages(stage_content):
    """Parse parallel stages and return them as separate jobs."""
    parallel_jobs = re.findall(r"stage\(['\"](.*?)['\"]\)\s*\{(.*?)\}", stage_content, re.DOTALL)
    job_map = {}

    for job_name, job_content in parallel_jobs:
        job_map[job_name] = parse_steps(job_content)

    return job_map


def parse_steps(stage_content):
    """Parse individual steps in a stage."""
    steps = re.findall(r"(sh|echo|env)\s+['\"](.*?)['\"]", stage_content)
    job_steps = []

    for step_type, command in steps:
        if step_type == "sh":
            job_steps.append({"run": command})
        elif step_type == "echo":
            job_steps.append({"run": f"echo {command}"})
        elif step_type == "env":
            var, value = command.split("=")
            job_steps.append({"env": {var.strip(): value.strip()}})

    return job_steps


def parse_post_actions(stage_content):
    """Parse post actions for success and failure conditions."""
    post_actions = re.findall(r"(success|failure|always)\s*\{\s*(.*?)\s*\}", stage_content, re.DOTALL)
    actions = {}

    for condition, command in post_actions:
        actions[condition] = [{"run": f"echo {command.strip()}"}]

    return actions


def generate_github_actions_yaml(jobs):
    """Generate the GitHub Actions workflow YAML with matrix builds and post actions."""
    workflow = {
        "name": "CI",
        "on": ["push", "pull_request"],
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
            "steps": stage_details["steps"] if "steps" in stage_details else []
        }

        # Add parallel jobs if present
        if "parallel" in stage_details:
            for parallel_stage, parallel_steps in stage_details["parallel"].items():
                parallel_job_name = f"{job_name}_{parallel_stage.lower().replace(' ', '_')}"
                workflow["jobs"][parallel_job_name] = {
                    "runs-on": "ubuntu-latest",
                    "steps": parallel_steps
                }
        
        # Add post actions (success/failure)
        if "post" in stage_details:
            for condition, steps in stage_details["post"].items():
                if condition == "success":
                    job["steps"].append({"if": "${{ success() }}", "run": steps[0]["run"]})
                elif condition == "failure":
                    job["steps"].append({"if": "${{ failure() }}", "run": steps[0]["run"]})

        # Add matrix build example (for Python versions)
        if "Build" in stage_name:
            job["strategy"] = {
                "matrix": {
                    "python": ["3.7", "3.8", "3.9"]
                }
            }
            job["steps"].insert(0, {"run": "echo Running in Python version ${{ matrix.python }}"})

        workflow["jobs"][job_name] = job

    return yaml.dump(workflow, default_flow_style=False)


def main():
    parser = argparse.ArgumentParser(description="Convert Jenkinsfile to GitHub Actions workflow with matrix builds and post actions.")
    parser.add_argument("jenkinsfile", help="Path to the Jenkinsfile")
    parser.add_argument("output", help="Path to save the GitHub Actions YAML file")

    args = parser.parse_args()

    try:
        with open(args.jenkinsfile, "r") as jf:
            jenkinsfile_content = jf.read()

        jobs = parse_jenkinsfile(jenkinsfile_content)
        github_actions_yaml = generate_github_actions_yaml(jobs)

        with open(args.output, "w") as gh_yaml:
            gh_yaml.write(github_actions_yaml)

        print(f"GitHub Actions workflow with matrix builds and post actions has been saved to {args.output}")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
