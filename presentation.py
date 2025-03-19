from auth import google_slide_auth
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from slide import Slide
from util import call_api_decorator
from PIL import Image
import requests
import io

class Presentation:
    def __init__(self, presentation_id):
        # Authentication Google Slide API
        creds = google_slide_auth()

        self.presentation_id = presentation_id
        self.service = build("slides", "v1", credentials=creds)

        # Call the Slides API
        try:
            self.presentation = (
                self.service.presentations().get(presentationId=self.presentation_id).execute()
            )
        except HttpError as e:
            print(e)

        self.slides = self.presentation.get("slides")

    @call_api_decorator
    def call_batch_update(self, requests):
        body = {"requests": requests}
        response = self.service.presentations().batchUpdate(
            presentationId=self.presentation_id, body=body
        ).execute()

        return response

    def delete_slide(self, page):
        page_id = Slide.get_page_id(self.slides, page)
        requests = [
            {
                'deleteObject': {
                    'objectId': page_id
                }
            }
        ]

        return self.call_batch_update(requests)

    def copy_slide(self, page):
        page_id = Slide.get_page_id(self.slides, page)
        requests = [
            {
                "duplicateObject": {
                    "objectId": page_id,
                }
            }
        ]

        return self.call_batch_update(requests)

    def move_slide(self, page, position):
        page_id = Slide.get_page_id(self.slides, page)
        requests = [
            {
                "updateSlidesPosition": {
                    "slideObjectIds": [
                            page_id,
                        ],
                        "insertionIndex": position
                    }
                }
        ]

        return self.call_batch_update(requests)

    def generate_thumbnail(self, page, output_path, thumbnail_properties):
        try:
            page_id = Slide.get_page_id(self.slides, page)
            params = {'pageObjectId': page_id}

            # Customize thumbnail generation if properties are provided
            # if thumbnail_properties:
            #     if 'mimeType' in thumbnail_properties:
            #         params['mimeType'] = thumbnail_properties['mimeType']
            #     if 'width' in thumbnail_properties:
            #         params['thumbnailProperties.width'] = thumbnail_properties['width']
            #     if 'height' in thumbnail_properties:
            #         params['thumbnailProperties.height'] = thumbnail_properties['height']

            response = self.service.presentations().pages().getThumbnail(
                presentationId=self.presentation_id,
                **params
            ).execute()

            # Extract the thumbnail URL
            thumbnail_url = response.get('contentUrl')

            # Download the thumbnail image
            img_data = requests.get(thumbnail_url).content
            img = Image.open(io.BytesIO(img_data))
            img.save(output_path)

            print(f"Thumbnail saved to '{output_path}'")
        except HttpError as e:
            print(e)