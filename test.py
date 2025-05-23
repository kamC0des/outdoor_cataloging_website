import boto3
s3 = boto3.client('s3')
with open("leo.jpg", "rb") as f:
    s3.upload_fileobj(f, "gearshare-2025swe-bucket", "leo.jpg")
