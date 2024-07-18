import boto3
import requests
import json
import time
import uuid

# AWS credentials and region
AWS_ACCESS_KEY = "your-ak"
AWS_SECRET_KEY = "your-sk"
AWS_REGION = "us-east-1"

# S3 bucket name from cloudformation output
S3_BUCKET_NAME = "inkcore-corebucket-xxxx"

# API endpoint from cloudformation output
API_ENDPOINT = "https://xxxxx.lambda-url.us-east-1.on.aws"

def upload_to_s3(file_path, bucket_name, object_name=None):
    """Upload a file to an S3 bucket and return the S3 URL"""
    if object_name is None:
        object_name = file_path.split("/")[-1]
    
    s3_client = boto3.client('s3', 
                             aws_access_key_id=AWS_ACCESS_KEY,
                             aws_secret_access_key=AWS_SECRET_KEY,
                             region_name=AWS_REGION)
    
    s3_client.upload_file(file_path, bucket_name, object_name)
    
    s3_url = f"s3://{bucket_name}/{object_name}"
    return s3_url

def download_from_s3(bucket_name, object_key, file_name):
    """Download a file from an S3 bucket"""
    s3_client = boto3.client('s3', 
                             aws_access_key_id=AWS_ACCESS_KEY,
                             aws_secret_access_key=AWS_SECRET_KEY,
                             region_name=AWS_REGION)
    
    s3_client.download_file(bucket_name, object_key, file_name)
    print(f"File downloaded as {file_name}")

def start_translation_job(document_url):
    """Start a document translation job and return the job ID"""
    url = f"{API_ENDPOINT}/api/v1/generation/translate/document"
    unique_job_id = str(uuid.uuid4())
    
    payload = {
        "id": unique_job_id,
        "url": document_url,
        "option": {
            "sourceLanguage": "EN_US",
            "targetLanguage": "ZH_CN",
            "model": "CLAUDE_3_HAIKU",
            "glossaries": []
        }
    }
    
    response = requests.post(url, json=payload, auth=aws4_auth)
    
    if response.status_code == 201:
        return json.loads(response.text)["id"]
    else:
        raise Exception(f"Failed to start translation job: {response.text}")

def check_translation_status(job_id):
    """Check the status of a translation job"""
    url = f"{API_ENDPOINT}/api/v1/generation/translate/document/{job_id}"
    
    response = requests.get(url, auth=aws4_auth)
    
    if response.status_code == 201:
        return json.loads(response.text)
    else:
        raise Exception(f"Failed to check translation status: {response.text}")

def aws4_auth(request):
    """AWS4 Authentication for requests"""
    from botocore.auth import SigV4Auth
    from botocore.awsrequest import AWSRequest
    from botocore.credentials import Credentials
    
    credentials = Credentials(AWS_ACCESS_KEY, AWS_SECRET_KEY)
    aws_request = AWSRequest(method=request.method, url=request.url, data=request.body)
    SigV4Auth(credentials, "lambda", AWS_REGION).add_auth(aws_request)
    request.headers.update(dict(aws_request.headers))
    return request

def main():
    # Step 1: Upload document to S3
    local_file_path = "2311.16452v1.pdf"
    s3_url = upload_to_s3(local_file_path, S3_BUCKET_NAME)
    print(f"Document uploaded to S3: {s3_url}")

    # Step 2: Start translation job
    job_id = start_translation_job(s3_url)
    print(f"Translation job started with ID: {job_id}")

    # Step 3: Check translation status until completed
    while True:
        status = check_translation_status(job_id)
        if status["status"] == "SUCCEEDED":
            print("Translation completed successfully!")
            print("Result:", status)
            
            # Download the translated document
            result = status
            bucket = result["location"]["bucket"]
            key = result["location"]["key"]
            download_from_s3(bucket, key, "translated_document.pdf")
            break
        elif status["status"] == "RUNNING" or status["status"] == "CREATED":
            print("Translation is still in progress. Waiting...")
            time.sleep(10)  # Wait for 60 seconds before checking again
        else:
            print(f"Translation failed with status: {status["status"]}")
            break

if __name__ == "__main__":
    main()