from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from .google_slide_auth import google_slide_auth
from .util import call_api_decorator
import uuid
from PIL import Image
import requests
import io

class SlideOps:
    def __init__(self, presentation_id, page):
        # Authentication Google Slide API
        creds = google_slide_auth()

        self.presentation_id = presentation_id
        self.service = build("slides", "v1", credentials=creds)

        # Call the Slides API
        try:
            self.presentation = (
                self.service.presentations().get(presentationId = self.presentation_id).execute()
            )
        except HttpError as e:
            print(e)

        self.slides = self.presentation.get("slides")
        self.page = page
        self.page_id = self.get_page_id()

    def get_page_id(self):
        return self.slides[self.page].get('objectId')

    def get_text_objects(self):
        text_obj_id = []

        for element in self.slides[self.page].get('pageElements'):
            if 'shape' in element.keys() and 'text' in element['shape'].keys():
            # if 'image' in element.keys():     # Get image IDs
                text_obj_id.append(element['objectId'])

        return text_obj_id

    def get_image_objects(self):
        image_obj_id = []

        for element in self.slides[self.page].get('pageElements'):
            if 'image' in element.keys():     # Get image IDs
                image_obj_id.append(element['objectId'])

        return image_obj_id

    def delete_text_from_textbox(self, textbox_id):
        requests = {
            "deleteText":
                {
                    "objectId": textbox_id,
                    "textRange": {"type": "ALL"}
                }
        }

        return requests

    def insert_plain_text(self, textbox_id, text):
        response = {
            "insertText": {
                "objectId": textbox_id,
                "insertionIndex": 0,
                "text": text,
            }
        }

        return response

    def insert_bullet_list(self, textbox_id, content):
        requests = [
            {
                "insertText": {
                    "objectId": textbox_id,
                    "text": content,
                    "insertionIndex": 0
                }
            },
            {
                "createParagraphBullets": {
                    "objectId": textbox_id,
                    "bulletPreset": "BULLET_DISC_CIRCLE_SQUARE",
                    "textRange": {
                        "type": "ALL"
                    }
                }
            }
        ]

        return requests

    def insert_image(self, shape_id, image_url):
        element = None
        for page_element in self.slides[self.page]['pageElements']:
            if page_element.get('objectId') == shape_id:
                element = page_element
                break

        if element is None:
            print(f"Shape with ID '{element}' not found on slide {self.page + 1}")
            return

        transform = element.get('transform')
        width = element.get('size', {}).get('width', {}).get('magnitude')
        height = element.get('size', {}).get('height', {}).get('magnitude')

        if transform:
            scaleX = transform.get('scaleX')
            scaleY = transform.get('scaleY')
            translateX = transform.get('translateX')
            translateY = transform.get('translateY')
            unit = transform.get('unit')
        else:
            print("Transform not found for shape.")
            return

        # 3. Create the requests to:
        #    - Delete the existing shape
        #    - Create a new image with the same size and position
        requests = [
                {
                    'deleteObject': {
                        'objectId': shape_id
                    }
                },
                {
                    'createImage': {
                        'objectId': f'{shape_id}_new_image',  # New object ID
                        'url': image_url,
                        'elementProperties': {
                            'pageObjectId': self.get_page_id(),
                            'size': {
                                'width': {
                                    'magnitude': width,
                                    'unit': unit
                                },
                                'height': {
                                    'magnitude': height,
                                    'unit': unit
                                }
                            },
                            'transform': {
                                'scaleX': scaleX,
                                'scaleY': scaleY,
                                'translateX': translateX,
                                'translateY': translateY,
                                'unit': unit
                            }
                        }
                    }
                }
            ]

        return requests

    def insert_table(self, table_id, n_rows, n_cols):
        requests = [
            {
                "createTable": {
                    "objectId": table_id,
                    "elementProperties": {
                        "pageObjectId": self.page_id,
                    },
                    "rows": n_rows,
                    "columns": n_cols
                }
            }
        ]

        return requests

    def edit_table_cell(self, table_id, row_idx, col_idx, text):
        requests = [
            {
                "insertText": {
                    "objectId": table_id,
                    "cellLocation": {
                        "rowIndex": row_idx,
                        "columnIndex": col_idx
                    },
                    "text": text,
                    "insertionIndex": 0
                }
            }
        ]

        return requests

    def make_cover_page(self, title, sub_title):
        textboxes = self.get_text_objects()
        requests = [
            self.delete_text_from_textbox(textboxes[0]),
            self.insert_plain_text(textboxes[0], title),

            self.delete_text_from_textbox(textboxes[1]),
            self.insert_plain_text(textboxes[1], sub_title),
        ]

        return self.call_batch_update(requests)

    def make_text_page(self, title, bullet_items):
        textboxes = self.get_text_objects()

        requests = [
            self.delete_text_from_textbox(textboxes[0]),
            self.insert_plain_text(textboxes[0], text=title),

            self.delete_text_from_textbox(textboxes[1]),
        ] + self.insert_bullet_list(textboxes[1], bullet_items)

        return self.call_batch_update(requests)

    def make_text_and_image_page(self, title, body_text, image_urls):
        textboxes = self.get_text_objects()
        image_shapes = self.get_image_objects()

        requests = [
            self.delete_text_from_textbox(textboxes[0]),
            self.insert_plain_text(textboxes[0], text=title),
            self.delete_text_from_textbox(textboxes[1])
        ] + self.insert_bullet_list(textboxes[1], content)

        for i, url in enumerate(image_urls):
            requests += self.insert_image(image_shapes[i], image_url=url)

        return self.call_batch_update(requests)

    def make_table_page(self, title, table_content):
        table_id = str(uuid.uuid4())
        n_row, n_col = len(table_content), len(table_content[0])
        requests = self.insert_table(table_id, n_row, n_col)

        for i in range(n_row):
            for j in range(n_col):
                requests += self.edit_table_cell(
                    table_id,
                    row_idx = i,
                    col_idx = j,
                    text = table_content[i][j]
                )

        return self.call_batch_update(requests)


    @call_api_decorator
    def call_batch_update(self, requests):
        body = {"requests": requests}
        response = self.service.presentations().batchUpdate(
            presentationId = self.presentation_id, body=body
        ).execute()

        return response

    def delete_slide(self):
        requests = [
            {
                'deleteObject': {
                    'objectId': self.page_id
                }
            }
        ]

        return self.call_batch_update(requests)

    def copy_slide(self):
        requests = [
            {
                "duplicateObject": {
                    "objectId": self.page_id,
                }
            }
        ]

        return self.call_batch_update(requests)

    def move_slide(self, position):
        requests = [
            {
                "updateSlidesPosition": {
                    "slideObjectIds": [
                            self.page_id,
                        ],
                        "insertionIndex": position
                    }
                }
        ]

        return self.call_batch_update(requests)

    def generate_thumbnail(self, output_path, thumbnail_properties):
        try:
            params = {'pageObjectId': self.page_id}

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


if __name__ == "__main__":
    PRESENTATION_ID = "1DHp7nE_loMyVXuE1i0FA3gW8DGkyZs-s1JFbqI_fttc"

    # slide = SlideOps(PRESENTATION_ID, page=0)
    # text_objects = slide.get_text_objects()
    #
    # print(slide.make_cover_page("Hello, Google Slide API", "Hari"))

    # slide = SlideOps(PRESENTATION_ID, page=2)
    # title = "Types of AI?"
    # content = "Computer Vision\n\tNatural Language Processing\n\t\tMachine Learning\n\t\t\tReinforcement Learning"
    # print(slide.make_text_page(title, content))

    slide = SlideOps(PRESENTATION_ID, page=8)
    title = "Types of AI?"
    content = "Computer Vision\n\tNatural Language Processing\n\t\tMachine Learning\n\t\t\tReinforcement Learning"
    image_urls = ["https://www.google.com/images/branding/googlelogo/2x/googlelogo_color_272x92dp.png"] * 2
    print(slide.make_text_and_image_page(title, content, image_urls))

    # slide = Slide(PRESENTATION_ID, page=2)
    # title = "Table Test"
    # table_content =  [
    #         ["Computer Vision", "NLP", "AI"],
    #         ["ML", "Reinforcement Learning", "Generative AI"]
    # ]
    #
    # print(slide.make_table_page(title, table_content))

    # slide = Slide(PRESENTATION_ID, page=10)
    # print(slide.delete_slide())

    # slide = Slide(PRESENTATION_ID, page=9)
    # print(slide.copy_slide())

    # slide = Slide(PRESENTATION_ID, page=9)
    # print(slide.move_slide(position=6))

    # slide = Slide(PRESENTATION_ID, page=5)
    # thumbnail_properties = {'mimeType': 'image/png'}
    # output_path = "thumbnail.png"
    # print(slide.generate_thumbnail(output_path, thumbnail_properties))