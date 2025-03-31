from PIL import Image
from google import genai
import boto3
from botocore.exceptions import ClientError
import json
import os
from dotenv import load_env

load_env()

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
BUCKET_NAME = 'slide-gen-images-bucket'

s3_client = boto3.client('s3')

# Create bucket if not exists
response = s3_client.create_bucket(
    Bucket = BUCKET_NAME
)

s3_client.put_public_access_block(
    Bucket=BUCKET_NAME,
    PublicAccessBlockConfiguration={
        'BlockPublicAcls': False,
        'IgnorePublicAcls': False,
        'BlockPublicPolicy': False,
        'RestrictPublicBuckets': False,
    },
)

# Create a bucket policy
bucket_policy = {
    'Version': '2012-10-17',
    'Statement': [{
        'Sid': 'PublicAccessBucket',
        'Effect': 'Allow',
        'Principal': '*',
        'Action': ['s3:GetObject', 's3:PutBucketPolicy'],
        'Resource': [
            f'arn:aws:s3:::{BUCKET_NAME}/*',
            f'arn:aws:s3:::{BUCKET_NAME}'
        ]
    }]
}

# Convert the policy from JSON dict to string
bucket_policy = json.dumps(bucket_policy)

# Set the new policy
s3_client.put_bucket_policy(Bucket=BUCKET_NAME, Policy=bucket_policy)

class ImageResource:
    def __init__(self, image_path, caption=None):
        # Path to local image
        self.image_path = image_path
        self.image = self.get_image()
        self.width, self.height = self.image.size

        if caption is not None:
            self.caption = caption
        else:
            self.caption = self.get_caption()

        self.image_url = self.upload_image_to_s3()

    def get_image(self):
        try:
            img = Image.open(self.image_path)
            return img

        except FileNotFoundError:
            return "File not found"
        except Exception as e:
            return f"An error occurred: {e}"

    def get_caption(self):
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=["Describe content of image neatly", self.image]
        )

        return response.text

    def upload_image_to_s3(self, acl="public-read"):
        # Upload the file
        s3_client = boto3.client('s3')

        try:
            s3_client.upload_file(
                self.image_path,
                BUCKET_NAME,
                self.image_path,
                ExtraArgs = {
                    'ContentType': 'image/jpeg',
                }
            )  # Set content type and make public.

            url = f"https://{BUCKET_NAME}.s3.amazonaws.com/{self.image_path}"
            print(f"File uploaded successfully. URL: {url}")

            return url

        except Exception as e:
            print(e)


if __name__ == "__main__":
    images = []
    IMG_DIR = "image"

    for img_path in os.listdir(IMG_DIR):
        img = ImageResource(image_path = f'{IMG_DIR}/{img_path}')
        images.append(img)