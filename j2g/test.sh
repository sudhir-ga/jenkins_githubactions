#!/bin/bash

# List of Jenkinsfiles to test
jenkinsfiles=("Jenkinsfile1" "Jenkinsfile2" "Jenkinsfile-complex")

for file in "${jenkinsfiles[@]}"; do
  echo "Testing with $file..."
  docker-compose run --rm jenkins-to-github "$file" "/app/output-${file}.yml"
  if [ $? -eq 0 ]; then
    echo "Test with $file succeeded!"
  else
    echo "Test with $file failed!"
    exit 1
  fi
done

