# Cloud Native Quote Generator Python App on EKS Cluster

## Overview

This project provides a step-by-step guide for containerizing a Python Flask application with Docker, uploading it to Amazon Elastic Container Registry (ECR), and deploying it on Amazon Elastic Kubernetes Service (EKS) using Kubernetes API and AWS SDK for Python (Boto3).

The Flask application is able to generate random quotes and display a quote of the day (qotd) using the [Quote Garden API](https://github.com/pprathameshmore/QuoteGarden). The project includes the necessary files and configurations to build the Docker image, push it to ECR, and deploy it on EKS.

## Prerequisites

1. Fork the repo and pull it down
2. Configure AWS Credentials
3. Python3, Docker, Kubectl and Eksctl installed.
4. Create [`eksClusterRole`](https://docs.aws.amazon.com/eks/latest/userguide/service_IAM_role.html) and [`eksNodeRole`](https://docs.aws.amazon.com/eks/latest/userguide/create-node-role.html) for cluster and node group creation.
5. Run the command `pip install -r requirements.txt` to install the required dependencies locally.

## Guide
1. Run the flask application locally using the command `python app.py`, Check `localhost:8000` on your browser to ensure the application is working correctly.
2. Run the command `docker build -t <image_name>` to build a docker image based on the provided `Dockerfile` in this repo.
3. Run the command `docker run -p 8000:8000 <image_name>` to run a docker container based on the created image. Check `localhost:8000` on your browser to ensure the application is working correctly.
4. Execute the `ecr.py` file using the command `python ecr.py`. This will create a ECR repository and output the repo's URI.
5. Push the created docker image to this repo using it's URI. Run the command `docker push <ecr_repo_uri>`.
6. Update the variables in the "Required cluster inputs" section if necessary. Execute the `eks.py` file using the command `python eks.py`.
7. Once the message: `Kubernetes service is now up and running! You can check the service locally by running the command kubectl port-forward service/my-flask-service 8000:8000` is displayed in the terminal, execute the command `kubectl port-forward service/my-flask-service 8000:8000`, you can then navigate to your browser and check `localhost:8000` to see the application working! 

