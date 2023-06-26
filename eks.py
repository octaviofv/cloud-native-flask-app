# Import dependencies
import boto3
import time
import os
import subprocess
from kubernetes import client, config
# Get VPC ID
def get_vpc_id(region):
    client = boto3.client("ec2", region_name=region)
    response = client.describe_vpcs()
    vpc_id = response["Vpcs"][0]["VpcId"]  # Assuming there is only one VPC
    return vpc_id
# Get Subnet IDs to use in EKS Cluster creation
def get_subnet_ids(vpc_id, region):
    client = boto3.client("ec2", region_name=region)
    response = client.describe_subnets(Filters=[{"Name": "vpc-id", "Values": [vpc_id]}])
    subnet_ids = [subnet["SubnetId"] for subnet in response["Subnets"] if not subnet["AvailabilityZone"].endswith("e")] #us-east-1e does not currently have sufficient capacity to support the cluster so exclude it.
    return subnet_ids
# Get Security Group IDs to use in EKS Cluster creation
def get_security_group_ids(vpc_id, region):
    client = boto3.client("ec2", region_name=region)
    response = client.describe_security_groups(Filters=[{"Name": "vpc-id", "Values": [vpc_id]}])
    security_group_ids = [sg["GroupId"] for sg in response["SecurityGroups"]]
    return security_group_ids
# Get ARN of specified role
def get_role_arn(role_name):
    client = boto3.client("iam", region_name=region)
    response = client.list_roles()
    for role in response["Roles"]:
        if role["RoleName"] == role_name:
            return role["Arn"]
    return None
# Get IAM username of configured user
def get_iam_username():
    client = boto3.client('sts')
    response = client.get_caller_identity()
    return response['Arn'].split('/')[-1]
# Get ARN of specified IAM username
def get_iam_user_arn(username):
    client = boto3.client("iam")
    response = client.get_user(UserName=username)
    return response["User"]["Arn"]
# Create EKS Cluster using gathered and entered information
def create_eks_cluster(cluster_name, subnet_ids, security_group_ids, role_arn, region):
    client = boto3.client('eks', region_name=region)
    response = client.create_cluster(
        name = cluster_name,
        version = "1.27",
        roleArn = role_arn,
        resourcesVpcConfig = {
            "subnetIds": subnet_ids,
            "securityGroupIds": [security_group_ids[0]]
        }
    )
    print("EKS cluster creation initiated. Cluster name:", cluster_name)
    return response
# Create Node Group for our created EKS Cluster with gathered and entered information
def create_node_group(nodegroup_name, cluster_name, subnet_ids, role_arn, region):
    client = boto3.client('eks', region_name=region)
    
    response = client.create_nodegroup(
        clusterName=cluster_name,
        nodegroupName=nodegroup_name,
        scalingConfig={
            'desiredSize': 2,
            'minSize': 1,
            'maxSize': 3
        },
        diskSize=20,
        subnets=subnet_ids,
        instanceTypes=['t2.micro'],
        amiType='AL2_x86_64',
        nodeRole=role_arn
    )
    print("Node group creation initiated. Node group name:", nodegroup_name)
    return response

# Wait for the EKS Cluster to become active
def wait_for_cluster_creation(cluster_name, region):
    client = boto3.client("eks", region_name=region)
    cluster_status = ""

    while cluster_status != "ACTIVE":
        response = client.describe_cluster(name=cluster_name)
        cluster_status = response["cluster"]["status"]
        print(f"EKS cluster '{cluster_name}' is still creating.")
        time.sleep(30)

    print(f"EKS cluster '{cluster_name}' is now active.")
# Wait for Node Group to become active
def wait_for_node_group_creation(cluster_name, nodegroup_name, region):
    client = boto3.client('eks', region_name=region)

    while True:
        response = client.describe_nodegroup(clusterName=cluster_name, nodegroupName=nodegroup_name)
        status = response['nodegroup']['status']

        if status == 'CREATING':
            print(f"Node group '{nodegroup_name}' is still creating. Current status: {status}")
            time.sleep(30)
        elif status == 'CREATE_FAILED':
            print(f"Node group '{nodegroup_name}' creation failed.")
            break
        elif status == 'DELETING':
            print(f"Node group '{nodegroup_name}' is being deleted.")
            time.sleep(30)
        elif status == 'DELETE_FAILED':
            print(f"Node group '{nodegroup_name}' deletion failed.")
            break
        elif status == 'UPDATING':
            print(f"Node group '{nodegroup_name}' is being updated.")
            time.sleep(30)
        elif status == 'UPDATE_FAILED':
            print(f"Node group '{nodegroup_name}' update failed.")
            break
        elif status == 'ACTIVE':
            print(f"Node group '{nodegroup_name}' is now active.")
            break
        else:
            print(f"Unknown status: {status}")
            break
# Get ECR Repo URI so we can use pushed docker image
def get_ecr_repository_uri(repository_name, region):
    client = boto3.client('ecr', region_name=region)
    response = client.describe_repositories(repositoryNames=[repository_name])
    repository_uri = response['repositories'][0]['repositoryUri']
    return repository_uri
# Grant IAM user Kubernetes permissions for our EKS cluster
def grant_kubernetes_permissions(username):
    # Authenticate as the IAM user
    subprocess.run(["aws", "eks", "update-kubeconfig", "--region", region, "--name", cluster_name], check=True)

    # Apply the Kubernetes RBAC configuration for granting permissions
    subprocess.run(["kubectl", "apply", "-f", "https://s3.us-west-2.amazonaws.com/amazon-eks/docs/eks-console-full-access.yaml"], check=True)

    # Get the IAM user's ARN
    user_arn = get_iam_user_arn(username)

    # Map IAM principal to Kubernetes user or group in aws-auth ConfigMap
    subprocess.run(["eksctl", "create", "iamidentitymapping", "--cluster", cluster_name, "--region", region, "--arn", user_arn, "--username", username, "--group", "system:masters"], check=True)

# Get the IP family of the cluster
def get_ip_family(cluster_name, region):
    response = subprocess.run(["aws", "eks", "describe-cluster", "--name", cluster_name, "--region", region], capture_output=True, text=True)
    ip_family = ""
    if response.returncode == 0:
        output = response.stdout.strip()
        for line in output.split("\n"):
            if "ipFamily" in line:
                ip_family = line.split(":")[1].strip().strip('"')
                break
    #Raise Error if unsuccessful
    if not ip_family:
        raise ValueError("Failed to retrieve IP family information for the cluster.")

    return ip_family

# Create and assign EKS VPC CNI Role to prevent network errors when deploying pods
def create_vpc_cni_iam_role(cluster_name, ip_family, eks_node_role, region):
    # Create the Amazon VPC CNI plugin for Kubernetes IAM role
    policy_arn = "" 
    if ip_family == "ipv4":
        policy_arn = "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
    elif ip_family == "ipv6":
        policy_arn = "arn:aws:iam::111122223333:policy/AmazonEKS_CNI_IPv6_Policy"  # Replace with your IPv6 policy ARN and Account ID!
    # Associate OIDC Provider and create IAMServiceAccount for our EKS Cluster
    subprocess.run(["eksctl", "utils", "associate-iam-oidc-provider", "--region", region, "--cluster", cluster_name, "--approve"])    
    subprocess.run(["eksctl", "create", "iamserviceaccount",
                    "--name", "aws-node",
                    "--namespace", "kube-system",
                    "--cluster", cluster_name,
                    "--region", region,
                    "--role-name", "AmazonEKSVPCCNIRole",
                    "--attach-policy-arn", policy_arn,
                    "--override-existing-serviceaccounts",
                    "--approve"],
                   check=True)
    # Make sure Node Group has necessary permissions
    subprocess.run(["aws", "iam", "attach-role-policy", "--role-name", eks_node_role, "--policy-arn", policy_arn])
    # Delete and re-create the Amazon VPC CNI plugin for Kubernetes Pods with these updates
    subprocess.run(["kubectl", "delete", "pods", "-n", "kube-system", "-l", "k8s-app=aws-node"], check=True)
    subprocess.run(["kubectl", "get", "pods", "-n", "kube-system", "-l", "k8s-app=aws-node"], check=True)   

# Create and deploy Kubernetes Service for our Cluster
def create_kubernetes(ecr_repository_uri, cluster_name, region):
    kubeconfig_path = os.path.expanduser("~/.kube/config")
    
    if not os.path.exists(kubeconfig_path):
        # Generate kubeconfig using AWS CLI command
        cluster_name = cluster_name
        region = region
        os.system(f"aws eks update-kubeconfig --name {cluster_name} --region {region}")
        print("Generated kubeconfig using AWS CLI command.")
    
    # Load the Kubernetes configuration from default location
    config.load_kube_config()

    # Create a Kubernetes API client
    api_client = client.ApiClient()

    # Define the deployment
    deployment = client.V1Deployment(
        metadata=client.V1ObjectMeta(name="my-flask-app"),
        spec=client.V1DeploymentSpec(
            replicas=1,
            selector=client.V1LabelSelector(
                match_labels={"app": "my-flask-app"}
            ),
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(
                    labels={"app": "my-flask-app"}
                ),
                spec=client.V1PodSpec(
                    containers=[
                        client.V1Container(
                            name="my-flask-container",
                            image=f"{ecr_repository_uri}:latest",
                            ports=[client.V1ContainerPort(container_port=8000)]
                        )
                    ]
                )   
            )
        )
    )
    # Create the deployment
    api_instance = client.AppsV1Api(api_client)
    api_instance.create_namespaced_deployment(
        namespace="default",
        body=deployment
    )

    # Define the service
    service = client.V1Service(
        metadata=client.V1ObjectMeta(name="my-flask-service"),
        spec=client.V1ServiceSpec(
            selector={"app": "my-flask-app"},
            ports=[client.V1ServicePort(port=8000)]
        )
    )

    # Create the service
    api_instance = client.CoreV1Api(api_client)
    api_instance.create_namespaced_service(
        namespace="default",
        body=service
    )

    # Wait for the pod to reach the Running state
    api_instance = client.CoreV1Api()
    while True:
        pod_list = api_instance.list_namespaced_pod(namespace="default", label_selector="app=my-flask-app")
        if pod_list.items:
            pod_status = pod_list.items[0].status.phase
            if pod_status == "Running":
                print("Kubernetes service is now up and running! You can check the service locally by running the command kubectl port-forward service/my-flask-service 8000:8000 ")
                break
        time.sleep(10)


# Required cluster inputs
region = "us-east-1"
eks_cluster_role = "eksClusterRole"
eks_node_role = "eksNodeRole"
cluster_name = "test"
nodegroup_name = "test_node_group"
ecr_uri = "quote_app_image"
# IAM username to grant Kubernetes permissions
iam_username = get_iam_username()
# Function calls to create our EKS Cluster and Kubernetes Service for our cluster
ecr_repository_uri = get_ecr_repository_uri(ecr_uri, region)
vpc_id = get_vpc_id(region)
subnet_ids = get_subnet_ids(vpc_id, region)
security_group_ids = get_security_group_ids(vpc_id, region)
cluster_role_arn = get_role_arn(eks_cluster_role)
node_role_arn = get_role_arn(eks_node_role)
cluster = create_eks_cluster(cluster_name, subnet_ids, security_group_ids, cluster_role_arn, region)
wait_for_cluster_creation(cluster_name, region)
node_group = create_node_group(nodegroup_name, cluster_name, subnet_ids, node_role_arn, region)
wait_for_node_group_creation(cluster_name, nodegroup_name, region)
grant_kubernetes_permissions(iam_username)
ip_family = get_ip_family(cluster_name, region)
create_vpc_cni_iam_role(cluster_name, ip_family, eks_node_role, region)
create_kubernetes(ecr_repository_uri, cluster_name, region)



