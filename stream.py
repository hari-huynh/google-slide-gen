from pydantic_ai import Agent, RunContext
import chainlit as cl
from pydantic_ai.messages import (
    FinalResultEvent,
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    PartDeltaEvent,
    PartStartEvent,
    TextPartDelta,
    ToolCallPartDelta,
)
from chainlit.input_widget import TextInput
import webbrowser
from slide_agent.presentation_model import ImageData, Content, BulletPoints
from slide_agent.slide_gen import slide_gen_agent, delete_unnecessary_slide, copy_slide, move_slide, update_presentation_content

def prepare():
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

    return content, images

output_messages: list[str] = []

@cl.on_chat_start
async def start_chat():
    cl.user_session.set(
        "message_history",
        [{"role": "system", "content": "You are a helpful assistant."}],
    )

    settings = await cl.ChatSettings(
        [
            TextInput(id="google_slide_url", label="Google Slide URL"),
        ]
    ).send()

    await setup(settings)

@cl.on_settings_update
async def setup(settings):
    google_slide_url = settings["google_slide_url"]

    if google_slide_url:
        presentation_id = google_slide_url.split("/")[5]
        cl.user_session.set("presentation_id", presentation_id)

    cl.user_session.set("google_slide_url", google_slide_url)


@cl.set_starters
async def set_starters():
    return [
        cl.Starter(
            label="Create a presentation",
            message="Can you help me create a presentation",
            icon="/public/presentation.svg",
            )
    ]

@cl.on_message
async def main(message: cl.Message):
    message_history = cl.user_session.get("message_history")
    message_history.append({"role": "user", "content": message.content})

    msg = cl.Message(content="", elements=[])

    content, images = prepare()

    deps = Content(
        title="Attention is all you need",
        content=content,
        images=images,
        language="English"
    )

    task_list = cl.TaskList()
    task_list.status = "Running..."

    task1 = cl.Task(title="Synthesizing data for the presentation", status=cl.TaskStatus.RUNNING)
    await task_list.add_task(task1)
    await task_list.send()

    async with slide_gen_agent.iter("", deps=deps) as run:
        async for node in run:
            print(node)
            if Agent.is_user_prompt_node(node):
                # A user prompt node => The user has provided input
                output_messages.append(f'=== UserPromptNode: {node.user_prompt} ===')
                # await msg.stream_token(f'=== UserPromptNode: {node.user_prompt} ===')
            elif Agent.is_model_request_node(node):
                # A model request node => We can stream tokens from the model's request
                output_messages.append(
                    '=== ModelRequestNode: streaming partial request tokens ===\n'
                )
                # await msg.stream_token('=== ModelRequestNode: streaming partial request tokens ===\n')

                async with node.stream(run.ctx) as request_stream:
                    async for event in request_stream:
                        if isinstance(event, PartStartEvent):
                            output_messages.append(
                                f"[Request] Starting part {event.index}: {event.part!r}"
                            )
                            # await msg.stream_token(f"[Request] Starting part {event.index}: {event.part!r}")

                        elif isinstance(event, PartDeltaEvent):
                            if isinstance(event.delta, TextPartDelta):
                                output_messages.append(
                                    f'[Request] Part {event.index} text delta: {event.delta.content_delta!r}'
                                )
                                # await msg.stream_token(f'[Request] Part {event.index} text delta: {event.delta.content_delta!r}')
                            elif isinstance(event.delta, ToolCallPartDelta):
                                output_messages.append(
                                    f'[Request] Part {event.index} args.delta={event.delta.args_delta}'
                                )
                                # await msg.stream_token(f'[Request] Part {event.index} args.delta={event.delta.args_delta}')
                        elif isinstance(event, FinalResultEvent):
                            output_messages.append(
                                f'[Result] The model produced a final result (tool_name={event.tool_name}'
                            )
                            # await msg.stream_token(f'[Result] The model produced a final result (tool_name={event.tool_name}')
            elif Agent.is_call_tools_node(node):
                # A handle-response node => The model returned some data, potentially calls a tool
                output_messages.append(
                    '=== CallToolNode: streaming partial response & tool usage ==='
                )
                # await msg.stream_token('=== CallToolNode: streaming partial response & tool usage ===')

                async with node.stream(run.ctx) as handle_stream:
                    async for event in handle_stream:
                        if isinstance(event, FunctionToolCallEvent):
                            output_messages.append(
                                f'[Tools] The LLM calls tool={event.part.tool_name!r} with args={event.part.args} (tool_call_id={event.part.tool_call_id!r}'
                            )

                            # await msg.stream_token(f'[Tools] The LLM calls tool={event.part.tool_name!r} with args={event.part.args} (tool_call_id={event.part.tool_call_id!r}')
                        elif isinstance(event, FunctionToolResultEvent):
                            output_messages.append(
                                f'[Tools] Tool call {event.tool_call_id!r} returned => {event.result.content}'
                            )
                            # await msg.stream_token(f'[Tools] Tool call {event.tool_call_id!r} returned => {event.result.content}')
            elif Agent.is_end_node(node):
                assert run.result.data == node.data.data

                final_result = run.result.data
                # Once an End node is reached, the agent run is complete
                output_messages.append(f'=== Final Agent Output: {run.result.data} ===')

                for slide in run.result.data.slides:
                    await msg.stream_token(f"### PAGE {slide.page}: {slide.title}\n\n")

                    if isinstance(slide.body_text, BulletPoints):
                        await msg.stream_token(f"{slide.body_text.subject}\n")
                        for point in slide.body_text.points:
                            await msg.stream_token(f"- {point}\n")
                    else:
                        await msg.stream_token(f"{slide.body_text.text}\n")

                    if slide.image_urls:
                        await msg.stream_token(f"\nImages:\n\n")

                        for url in slide.image_urls:
                            await msg.stream_token(f"![]({url})")

                    await msg.stream_token("\n\n-------------------------------------\n\n")


    message_history.append({"role": "assistant", "content": msg.content})
    await msg.update()

    task1.status = cl.TaskStatus.DONE
    task2 = cl.Task(title="Prepare template for the presentation", status=cl.TaskStatus.RUNNING)

    PRESENTATION_ID = cl.user_session.get("presentation_id")
    target_layout = [slide.layout for slide in final_result.slides]
    curr_template = ["cover", "table content", "only text", "text, image 25%", "text and image equal, 50%-50%",
                "image, text 25%", "only image", "text and 4 images", "text and 2 images", "graph", "video",
                "closing"]
    task3 = cl.Task(title="Deleting unnecessary slide from the presentation", status=cl.TaskStatus.RUNNING)
    task4 = cl.Task(title="Duplicate slides from the presentation", status=cl.TaskStatus.RUNNING)
    task5 = cl.Task(title="Move slides to appropriate position", status=cl.TaskStatus.RUNNING)

    await task_list.add_task(task2)
    await task_list.add_task(task3)
    await task_list.send()

    # Delete unnecessary slides
    curr_template = delete_unnecessary_slide(PRESENTATION_ID, target_layout, curr_template)
    task3.status = cl.TaskStatus.DONE
    await task_list.add_task(task4)
    await task_list.send()


    # Duplicate slides
    curr_template = copy_slide(PRESENTATION_ID, target_layout, curr_template)
    task4.status = cl.TaskStatus.DONE
    await task_list.add_task(task5)
    await task_list.send()

    # Move slides to the appropriate position
    curr_template = move_slide(PRESENTATION_ID, target_layout, curr_template)
    assert curr_template == target_layout
    task5.status = cl.TaskStatus.DONE
    task2.status = cl.TaskStatus.DONE
    await task_list.send()


    task6 = cl.Task(title="Update content of the presentation", status=cl.TaskStatus.RUNNING)
    await task_list.add_task(task6)
    await task_list.send()

    update_presentation_content(PRESENTATION_ID, final_result.slides)

    task6.status = cl.TaskStatus.DONE
    await task_list.send()

    thumbnails = [cl.Image(name = f"{i}", path=f"./thumbnail/{i}.png", display="inline") for i in range(17)]

    # Sending an action button within a chatbot message
    actions = [
        cl.Action(name="like", payload={"value": "example_value"}, label="", icon="thumbs-up"),
        cl.Action(name="dislike", payload={"value": "example_value"}, label="", icon="thumbs-down"),
        cl.Action(name="action_button", payload={"google_slide_url": cl.user_session.get("google_slide_url")},
                  label="Open with Google Slide",
                  icon="presentation"),
        cl.Action(name="download_button", payload={"value": "example_value"}, label="Download Presentation",
                  icon="download"),
    ]

    await cl.Message(
        content = "This is a presentation result",
        elements = thumbnails,
        actions = actions
    ).send()

@cl.action_callback("action_button")
async def on_action(action):
    webbrowser.open_new_tab(url = action.payload["google_slide_url"])
    # Optionally remove the action button from the chatbot user interface
    await action.remove()

google_slide_url = ""