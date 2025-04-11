import os
from pydantic_ai import Agent, RunContext
from typing import List, Union, Literal, Optional
from .google_slide_ops import SlideOps
from .presentation_model import Content, ImageData, Presentation, BulletPoints, Description
from dotenv import load_dotenv

load_dotenv()

slide_gen_agent = Agent(
    'google-gla:gemini-2.0-flash',
    deps_type=Content,
    result_type=Presentation,
    model_settings={"temperature": 0.0}
)

@slide_gen_agent.system_prompt
def system_prompt(ctx: RunContext[Content]) -> str:
    return f"""
    You are assistant agent to help me generate slides for presentation.
    Use provided information {ctx.deps.content} about {ctx.deps.title} to summarize and synthesize content for the presentation.
    Given the following images information. Given each slide have size 1920x1080 px:
    IMAGES:
    """ + "\n".join(
        [f"{image.image_url}: {image.caption} have size {image.width}x{image.height}" for image in ctx.deps.images])
    + """
    Firstly, use given information to summarize and synthesize content for the presentation.
    The first slide is COVER, only include title of the presentation and subtitle. 
    The last slide is CLOSING, only include "Thanks for watching".

    Secondly, select approriate image for the slide. If have not the suitable image for the slide, simply return `None`.
    Finally, select the most appropriate layout for this slide, based on whether slide have image and its size.


    MUST USE `only text` for slide which `image_url` is empty.
    USE `only image` for slide which have large image.
    Make sure content brevity BUT clarity and meaningful.
    """

def delete_unnecessary_slide(presentation_id, target, curr_template):
    slide_indexes = []
    for idx, curr in enumerate(curr_template):
        if curr not in target:
            slide_indexes.append(idx)
    slide_indexes = sorted(slide_indexes, reverse=True)

    requests = []

    for idx in slide_indexes:
        print(f"### DELETE SLIDE #{idx}")
        s = SlideOps(presentation_id, page=idx)

        requests += [
            {
                'deleteObject': {
                    'objectId': s.page_id
                }
            }
        ]

        curr_template.pop(idx)

    response = s.call_batch_update(requests)
    print(response)

    return curr_template


def copy_slide(presentation_id, target, curr_template):
    n_times = {}
    for temp in target:
        if temp in n_times.keys():
            n_times[temp] += 1
        else:
            n_times[temp] = 1

    slide_idx = 0
    while slide_idx < len(target):
        requests = []
        current_slide = curr_template[slide_idx]
        n = n_times[current_slide] - 1

        if n > 0:
            print(f"### COPY SLIDE #{slide_idx} {n} times")
            s = SlideOps(presentation_id, page=slide_idx)
            requests = [
                           {
                               "duplicateObject": {
                                   "objectId": s.page_id,
                               }
                           }
                       ] * n

            response = s.call_batch_update(requests)
            print(response)

            for i in range(n):
                curr_template.insert(slide_idx + (i + 1), current_slide)

            slide_idx = slide_idx + n + 1
        else:
            slide_idx += 1

    return curr_template

def move_slide(presentation_id, target, curr_template):
    for i, target_element in enumerate(target):
        # Skip element from i and find position of element
        current_idx = curr_template.index(target_element, i)
        if current_idx != i:
            print(f"### MOVE SLIDE #{current_idx} TO POSITION #{i}")
            s = SlideOps(presentation_id, page=current_idx)
            response = s.move_slide(i)

            # Update position of elements after moving
            orig_slide = curr_template.pop(current_idx)
            curr_template.insert(i, orig_slide)

    return curr_template


if __name__ == "__main__":
    with open('sample.txt', 'r', encoding='utf-8') as file:
        content = file.read()

    images = []

    images.append(
        ImageData(
            image_url="https://slide-gen-images-bucket.s3.amazonaws.com/image/0.jpg",
            caption='The graph displays the BLEU scores for various translation models, "RNNsearch-50", "RNNsearch-30", "RNNenc-50", and "RNNenc-30", plotted against sentence length.',
            width=793,
            height=442
        )
    )

    images.append(
        ImageData(
            image_url="https://slide-gen-images-bucket.s3.amazonaws.com/image/1.jpg",
            caption='This image depicts an encoder-decoder model with attention.',
            width=924,
            height=961
        )
    )

    images.append(
        ImageData(
            image_url="https://slide-gen-images-bucket.s3.amazonaws.com/image/2.jpg",
            caption='The image illustrates an attention mechanism in layer 5 of a neural network model, showing how input tokens relate to each other.',
            width=426,
            height=406
        )
    )

    images.append(
        ImageData(
            image_url="https://slide-gen-images-bucket.s3.amazonaws.com/image/3.jpg",
            caption='The image shows the formula for calculating attention in a neural network.',
            width=490,
            height=104
        )
    )

    images.append(
        ImageData(
            image_url="https://slide-gen-images-bucket.s3.amazonaws.com/image/4.jpg",
            caption='The image presents the mathematical formula for Multi-Head Attention.',
            width=1500,
            height=224
        )
    )

    images.append(
        ImageData(
            image_url="https://slide-gen-images-bucket.s3.amazonaws.com/image/5.jpg",
            caption='This image is a diagram of the Multi-Head Attention mechanism.',
            width=800,
            height=1086
        )
    )

    images.append(
        ImageData(
            image_url="https://slide-gen-images-bucket.s3.amazonaws.com/image/6.jpg",
            caption='This image illustrates the steps involved in multi-head attention, from embedding input to producing the output layer, using matrices and weight matrices.',
            width=953,
            height=504
        )
    )

    images.append(
        ImageData(
            image_url="https://slide-gen-images-bucket.s3.amazonaws.com/image/7.jpg",
            caption='The image shows the formula for calculating positional encoding in neural networks.',
            width=676,
            height=184
        )
    )

    images.append(
        ImageData(
            image_url="https://slide-gen-images-bucket.s3.amazonaws.com/image/8.jpg",
            caption='The image displays the sine method for positional encoding, showing a visual representation of sine and cosine functions across position and depth.',
            width=1928,
            height=938
        )
    )

    images.append(
        ImageData(
            image_url="https://slide-gen-images-bucket.s3.amazonaws.com/image/9.jpg",
            caption='The image contains mathematical equations representing transformations of sine and cosine functions, possibly related to signal processing or linear algebra.',
            width=824,
            height=324
        )
    )

    images.append(
        ImageData(
            image_url="https://slide-gen-images-bucket.s3.amazonaws.com/image/10.jpg",
            caption='The image displays a detailed architecture diagram of a transformer model with encoder and decoder components, highlighting key features such as attention mechanisms, feed-forward networks, positional encoding, and residual connections with layer normalization.',
            width=1246,
            height=714
        )
    )

    images.append(
        ImageData(
            image_url="https://slide-gen-images-bucket.s3.amazonaws.com/image/11.jpg",
            caption='The image is a table comparing the BLEU scores and training costs (in FLOPs) of various machine translation models, including the Transformer model, on English-to-German (EN-DE) and English-to-French (EN-FR) translation tasks.',
            width=844,
            height=378
        )
    )

    deps = Content(
        title="Attention is all you need",
        content=content,
        images=images,
        language="English"
    )

    result = slide_gen_agent.run_sync("", deps=deps)
    print(result)

    # -------------------------------------------------------------------------------
    # Edit presentation

    layouts = [slide.layout for slide in result.data.slides]
    print(layouts)

    PRESENTATION_ID = "1grCs_IvDi99S5WHHBEajo4E_nb3P1UySIycvEk1tVfA"

    template = ["cover", "table content", "only text", "text, image 25%", "text and image equal, 50%-50%",
                "image, text 25%", "only image", "text and 4 images", "text and 2 images", "graph", "video",
                "closing"]

    # deps = PrepareSlideDeps(
    #     presentation_id = PRESENTATION_ID,
    #     layout = str(layouts),
    #     current_template = template
    # )
    #
    # result = prepare_presentation_agent.run_sync("", deps=deps)
    # print(result)

    curr_template = delete_unnecessary_slide(PRESENTATION_ID, layouts, template)
    curr_template = copy_slide(PRESENTATION_ID, layouts, curr_template)
    curr_template = move_slide(PRESENTATION_ID, layouts, curr_template)
    assert curr_template == layouts

def update_presentation_content(presentation_id, slides):
    for i, slide in enumerate(slides):
        s = SlideOps(presentation_id, page=i)

        # Get Textbox
        textboxes = s.get_text_objects()

        # Insert Title
        requests = [
            s.delete_text_from_textbox(textboxes[0]),
            s.insert_plain_text(textboxes[0], text=slide.title),
            s.delete_text_from_textbox(textboxes[1])
        ]

        if isinstance(slide.body_text, BulletPoints):
            # Insert bullet list
            bullet_items = slide.body_text.subject + "\n\t" + "\n\t".join(slide.body_text.points)
            requests += s.insert_bullet_list(textboxes[1], bullet_items)
        elif isinstance(slide.body_text, Description):
            requests.append(
                s.insert_plain_text(textboxes[1], text=slide.body_text.text + "\n")
            )

        # Get image shapes
        image_shapes = s.get_image_objects()

        for i, img_url in enumerate(slide.image_urls):
            requests += s.insert_image(image_shapes[i], img_url)

        # Call batch update
        s.call_batch_update(requests)
        print(f"Updated content slide #{i + 1}")
