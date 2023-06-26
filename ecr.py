import boto3

client = boto3.client('ecr', region_name='us-east-1')

repository_name = "quote_app_image"
response = client.create_repository(repositoryName=repository_name)

repository_uri = response ['repository']['repositoryUri']
print(repository_uri)