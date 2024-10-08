import base64
import logging
import os

import gradio as gr
from openai import OpenAI, OpenAIError

from modules import scripts
from modules.processing import StableDiffusionProcessingTxt2Img
# from modules.script_callbacks import on_ui_tabs
from modules.shared import opts

log = logging.getLogger("[auto-llm]")
# log.setLevel(logging.INFO)
# Logging
log_file = os.path.join(scripts.basedir(), "auto-llm.log")

random_symbol = '\U0001f3b2\ufe0f'  # 🎲️
reuse_symbol = '\u267b\ufe0f'  # ♻️
paste_symbol = '\u2199\ufe0f'  # ↙
refresh_symbol = '\U0001f504'  # 🔄
save_style_symbol = '\U0001f4be'  # 💾
apply_style_symbol = '\U0001f4cb'  # 📋
clear_prompt_symbol = '\U0001f5d1\ufe0f'  # 🗑️
extra_networks_symbol = '\U0001F3B4'  # 🎴
switch_values_symbol = '\U000021C5'  # ⇅
restore_progress_symbol = '\U0001F300'  # 🌀
detect_image_size_symbol = '\U0001F4D0'  # 📐


# sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8')
# sys.stderr = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8')


def _get_effective_prompt(prompts: list[str], prompt: str) -> str:
    return prompts[0] if prompts else prompt


class AutoLLM(scripts.Script):
    client = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")
    llm_history_array = []
    llm_history_array_eye = []
    llm_sys_vision_template = ("This is a chat between a user and an assistant. The assistant is helping the user to describe an image.")

    llm_sys_text_template = ("You are an AI prompt word engineer. Use the provided keywords to create a beautiful composition. Only the prompt words are needed, not your feelings. Customize the style, scene, decoration, etc., and be as detailed as possible without endings.")
    llm_sys_translate_template = ("You are a professional and literary Taiwanese translation expert."
                                  "Please follow the following rules to translate into Taiwanese Traditional Chinese:)"
                                  "\n- Only the translated text is returned without any explanation."
                                  "\n- Language: Use Traditional Chinese and Taiwanese idioms for translation, do not use Simplified Chinese and Chinese idioms."
                                  "\n- Style: In line with Taiwanese writing habits, it is smooth and easy to read, and strives to be literary and meaningful."
                                  "\n- Nouns: Translate movie titles, book titles, authors, and artist names using Taiwanese common translation methods. Noun translations within the same article must be consistent."
                                  "\n- Format: All punctuation marks must be full-width, with spaces between Chinese and English."
                                  "\n- Each sentence should not exceed 30 words."
                                  "\n- Avoid inverted sentences.")

    def __init__(self) -> None:
        self.YOU_LLM = "A superstar on stage."
        super().__init__()

    def title(self):
        return "Dynamic Javascript Prompt"

    def show(self, is_img2img):
        return scripts.AlwaysVisible

    def check_api_uri(self, llm_apiurl, llm_apikey):
        if self.client.base_url != llm_apiurl or self.client.api_key != llm_apikey:
            self.client = OpenAI(base_url=llm_apiurl, api_key=llm_apikey)

    def call_llm_eye_open(self, llm_apiurl, llm_apikey, llm_api_model_name, llm_system_prompt_eye, llm_ur_prompt_eye,
                          llm_ur_prompt_image_eye, llm_tempture_eye,
                          llm_max_token_eye, llm_api_translate_system_prompt,
                          llm_api_translate_enabled):
        base64_image = ""
        path_maps = {
            "txt2img": opts.outdir_samples or opts.outdir_txt2img_samples,
            "img2img": opts.outdir_samples or opts.outdir_img2img_samples,
            "txt2img-grids": opts.outdir_grids or opts.outdir_txt2img_grids,
            "img2img-grids": opts.outdir_grids or opts.outdir_img2img_grids,
            "Extras": opts.outdir_samples or opts.outdir_extras_samples
        }
        # https: // platform.openai.com / docs / guides / vision?lang = curl
        try:
            image = open(llm_ur_prompt_image_eye, "rb").read()
            base64_image = base64.b64encode(image).decode("utf-8")
            # print("[][call_llm_eye_open][]base64_image", base64_image)

        except Exception as e:
            # log.error(f"[][][call_llm_eye_open]IO Error: {e}")
            self.llm_history_array.append(["missing input image ?", e, e, e])
            # return "[][call_llm_eye_open]missing input image ?" + e, self.llm_history_array
            return "missing input image ?", self.llm_history_array
        try:
            self.check_api_uri(llm_apiurl, llm_apikey)

            completion = self.client.chat.completions.create(
                model=f"{llm_api_model_name}",
                messages=[
                    {
                        "role": "system",
                        "content": f"{llm_system_prompt_eye}",
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": f"{llm_ur_prompt_eye}"},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                },
                            },
                        ],
                    }
                ],
                max_tokens=llm_max_token_eye,
                temperature=llm_tempture_eye,
            )

        except OpenAIError as e:
            log.error(f"[][][call_llm_eye_open]Model Error: {e.message}")
            self.llm_history_array.append([e.message, e.message, e.message, e.message])
            return e.message, self.llm_history_array

        # for chunk in completion:
        #     if chunk.choices[0].delta.content:
        #         result = chunk.choices[0].delta.content
        # print(chunk.choices[0].delta.content, end="", flush=True)
        result = completion.choices[0].message.content
        result = result.replace('\n', ' ')
        result_translate = ""
        if llm_api_translate_enabled:
            result_translate = self.call_llm_translate(llm_api_model_name, llm_api_translate_system_prompt, result,
                                                       llm_max_token_eye)
        self.llm_history_array.append([result, llm_system_prompt_eye, llm_ur_prompt_eye, result_translate])
        if len(self.llm_history_array) > 3:
            self.llm_history_array.remove(self.llm_history_array[0])
        print("[][auto-llm][call_llm_eye_open] ", result)

        return result, self.llm_history_array

    def call_llm_pythonlib(self, llm_apiurl, llm_apikey, llm_api_model_name, llm_system_prompt, llm_ur_prompt,
                           llm_max_token, llm_tempture,
                           llm_recursive_use, llm_keep_your_prompt_use, llm_api_translate_system_prompt,
                           llm_api_translate_enabled):

        if llm_recursive_use and (self.llm_history_array.__len__() > 1):
            llm_ur_prompt = (llm_ur_prompt if llm_keep_your_prompt_use else "") + " " + \
                            self.llm_history_array[self.llm_history_array.__len__() - 1][0]
        try:
            self.check_api_uri(llm_apiurl, llm_apikey)

            completion = self.client.chat.completions.create(
                model=f"{llm_api_model_name}",
                messages=[
                    {"role": "system", "content": llm_system_prompt},
                    {"role": "user", "content": llm_ur_prompt}
                ],
                max_tokens=llm_max_token,
                temperature=llm_tempture,

            )
        except OpenAIError as e:
            self.llm_history_array.append([e.message, e.message, e.message, e.message])
            return e.message, self.llm_history_array

        result = completion.choices[0].message.content
        result = result.replace('\n', ' ')
        result_translate = ""
        if llm_api_translate_enabled:
            result_translate = self.call_llm_translate(llm_api_model_name, llm_api_translate_system_prompt, result,
                                                       llm_max_token)

        self.llm_history_array.append([result, llm_ur_prompt, llm_system_prompt, result_translate])
        if len(self.llm_history_array) > 3:
            self.llm_history_array.remove(self.llm_history_array[0])
        # print("[][auto-llm][call_llm_pythonlib] ", result, result_translate)

        return result, self.llm_history_array

    def call_llm_translate(self, llm_api_model_name, llm_api_translate_system_prompt, llm_api_translate_user_prompt,
                           _llm_max_token):
        try:

            completion2 = self.client.chat.completions.create(
                model=f"{llm_api_model_name}",
                messages=[
                    {"role": "system", "content": llm_api_translate_system_prompt},
                    {"role": "user", "content": llm_api_translate_user_prompt}
                ],
                max_tokens=_llm_max_token,
                temperature=0.2,
            )
        except OpenAIError as e:
            log.error(f"[][][call_llm_pythonlib]Error: {e.message}")
            return e.message
        result_translate = completion2.choices[0].message.content
        result_translate = result_translate.replace('\n', '').encode("utf-8").decode()
        log.warning(f"[][][call_llm_translate]: {result_translate}")

        return result_translate

    def ui(self, is_img2img):
        # print("\n\n[][Init-UI][sd-webui-prompt-auto-llm]: " + str(is_img2img) + "\n\n")
        # log.error(f'[][][][][][Init-UI][sd-webui-prompt-auto-llm]: " + str({is_img2img})')
        examples = [
            ["The Moon's orbit around Earth has"],
            ["The smooth Borealis basin in the Northern Hemisphere covers 40%"],
        ]

        with gr.Blocks():
            # gr.Markdown("Blocks")
            with gr.Accordion(open=False, label="Auto LLM v20240723"):
                with gr.Tab("LLM-as-assistant"):
                    # with gr.Accordion(open=True, label="[Prompt]/[LLM-PythonLib]"):
                    gr.Markdown("* Generate forever mode \n"
                                "* Story board mode")
                    llm_is_enabled = gr.Checkbox(label=" Enable LLM-Answer to SD-prompt", value=False)
                    llm_recursive_use = gr.Checkbox(label=" Recursive-prompt. Use the prompt from last one🌀",
                                                    value=False)
                    llm_keep_your_prompt_use = gr.Checkbox(label=" Keep LLM-Your-Prompt ahead each request",
                                                           value=False)

                    with gr.Row():
                        with gr.Column(scale=2):
                            llm_system_prompt = gr.Textbox(label="1. [LLM-System-Prompt]", lines=20,
                                                           value=self.llm_sys_text_template,
                                                           placeholder=self.llm_sys_text_template
                                                           )
                        with gr.Column(scale=3):
                            llm_ur_prompt = gr.Textbox(label="2. [LLM-Your-Prompt]", lines=2,
                                                       value="A superstar on stage.",
                                                       placeholder="A superstar on stage.")
                            llm_tempture = gr.Slider(-2, 2, value=0.9, step=0.01,
                                                     label="LLM temperature", elem_id="llm_tempture",
                                                     interactive=True,
                                                     hint='temperature (Deterministic) <1 | >1 (More creative)')
                            # llm_top_k = gr.Slider(
                            #     elem_id="top_k_slider", label="LLM Top K", value=8, minimum=1, maximum=20, step=1,
                            #     interactive=True,
                            #     hint='Strategy is to sample from a shortlist of the top K tokens. This approach allows the other high-scoring tokens a chance of being picked.')
                            llm_llm_answer = gr.Textbox(inputs=self.process, show_copy_button=True, interactive=True,
                                                        label="3. [LLM-Answer]", lines=6, placeholder="LLM says.")
                            with gr.Row():
                                llm_sendto_txt2img = gr.Button("send to txt2img")

                                llm_sendto_img2img = gr.Button("send to img2img")

                            llm_max_token = gr.Slider(5, 500, value=50, step=5, label="LLM Max length(tokens)")

                    llm_history = gr.Dataframe(
                        interactive=True,
                        wrap=True,
                        label="History/StoryBoard",
                        headers=["llm_answer", "system_prompt", "ur_prompt", "result_translate"],
                        datatype=["str", "str", "str", "str"],
                        row_count=3,
                        col_count=(4, "fixed"),
                    )

                    llm_button = gr.Button("Call LLM above")

                with gr.Tab("LLM-vision"):
                    llm_is_open_eye = gr.Checkbox(label="Enable LLM-vision👀", value=False)
                    llm_is_open_eye_last_one_image = gr.Checkbox(
                        label="Auto look at last one image (auto put last image into Step.2)",
                        value=True)
                    with gr.Row():
                        with gr.Column(scale=2):
                            llm_system_prompt_eye = gr.Textbox(label=" 1.[LLM-System-Prompt-eye]", lines=10,
                                                               value=self.llm_sys_vision_template,
                                                               placeholder=self.llm_sys_vision_template)
                            llm_ur_prompt_eye = gr.Textbox(label=" 2.[Your-prompt]", lines=10,
                                                           value="What’s in this image?",
                                                           placeholder="What’s in this image?")
                        with gr.Column(scale=3):
                            llm_ur_prompt_image_eye = gr.Image(label="2. [Your-Image]", lines=1, type="filepath")
                            llm_tempture_eye = gr.Slider(-2, 2, value=0.9, step=0.01,
                                                         label="LLM temperature (Deterministic) <1 | >1 (More creative)")
                            llm_llm_answer_eye = gr.Textbox(inputs=self.process, show_copy_button=True,
                                                            interactive=True,
                                                            label="3. [LLM-Answer-eye]", lines=6,
                                                            placeholder="LLM says.")
                            llm_max_token_eye = gr.Slider(5, 500, value=50, step=5,
                                                          label="LLM Max length(tokens)")
                    llm_history_eye = gr.Dataframe(
                        interactive=True,
                        wrap=True,
                        label="History/StoryBoard",
                        headers=["llm_answer", "system_prompt", "ur_prompt", "result_translate"],
                        datatype=["str", "str", "str", "str"],
                        row_count=3,
                        col_count=(4, "fixed"),
                    )
                    llm_button_eye = gr.Button("Call LLM-vision above")

                # with gr.Tab("LLM-through-embeddings"):
                #     llm_is_through = gr.Checkbox(label="Enable LLM-through", value=False)
                #
                # with gr.Tab("LLM-asking-chat"):
                #     llm_is_asking = gr.Checkbox(label="Enable asking", value=False)
                # with gr.Tab("Gallery"):
                #     gallery = gr.Gallery(label="Generated images", show_label=False, elem_id="gallery", columns=3, rows=1, object_fit="contain", height="auto")

                with gr.Tab("Setup"):
                    gr.Markdown("* API-URI: LMStudio=>http://localhost:1234/v1 \n"
                                "* API-URI: ollama  => http://localhost:11434/v1 \n"
                                "* API-ModelName: LMStudio can be empty is fine select in LMStudio App; ollama should set like: ollama3.1 (cmd:ollama list)\n"
                                "* OLLAMA OpenAI compatibility https://ollama.com/blog/openai-compatibility\n"
                                )
                    llm_apiurl = gr.Textbox(
                        label="0.[LLM-URL] | LMStudio=>http://localhost:1234/v1 | ollama=> http://localhost:11434/v1",
                        lines=1,
                        value="http://localhost:1234/v1")
                    llm_apikey = gr.Textbox(label="0.[LLM-API-Key]", lines=1, value="lm-studio")
                    llm_api_model_name = gr.Textbox(label="0.[LLM-Model-Name]", lines=1,
                                                    placeholder="llama3.1, llama2, gemma2")
                    llm_api_translate_enabled = gr.Checkbox(
                        label="Enable translate LLM-answer to Your language.(won`t effect with SD, just for reference. )",
                        value=False)
                    llm_api_translate_system_prompt = gr.Textbox(label=" 0.[LLM-Translate-System-Prompt]", lines=2,
                                                                 value=self.llm_sys_translate_template)
        llm_button_eye.click(self.call_llm_eye_open,
                             inputs=[llm_apiurl, llm_apikey, llm_api_model_name, llm_system_prompt_eye,
                                     llm_ur_prompt_eye,
                                     llm_ur_prompt_image_eye, llm_tempture_eye,
                                     llm_max_token_eye, llm_api_translate_system_prompt,
                                     llm_api_translate_enabled],
                             outputs=[llm_llm_answer_eye, llm_history_eye])
        llm_button.click(self.call_llm_pythonlib,
                         inputs=[llm_apiurl, llm_apikey, llm_api_model_name, llm_system_prompt, llm_ur_prompt,
                                 llm_max_token, llm_tempture,
                                 llm_recursive_use, llm_keep_your_prompt_use, llm_api_translate_system_prompt,
                                 llm_api_translate_enabled],
                         outputs=[llm_llm_answer, llm_history])

        llm_sendto_txt2img.click(fn=None, _js="function(prompt){sendPromptAutoPromptLLM('txt2img', prompt)}", inputs=[llm_llm_answer])
        llm_sendto_img2img.click(fn=None, _js="function(prompt){sendPromptAutoPromptLLM('img2img', prompt)}", inputs=[llm_llm_answer])

        for e in [llm_llm_answer, llm_history, llm_llm_answer_eye, llm_history_eye]:
            e.do_not_save_to_config = True

        return [llm_is_enabled, llm_recursive_use, llm_keep_your_prompt_use,
                llm_system_prompt, llm_ur_prompt,
                # llm_llm_answer,
                # llm_history,
                llm_max_token, llm_tempture,
                llm_apiurl, llm_apikey, llm_api_model_name,
                llm_api_translate_system_prompt, llm_api_translate_enabled,
                llm_is_open_eye,
                # llm_is_open_eye_last_one_image,
                llm_system_prompt_eye, llm_ur_prompt_eye, llm_ur_prompt_image_eye,
                llm_tempture_eye,
                # llm_llm_answer_eye,
                llm_max_token_eye,
                # llm_history_eye,
                # llm_sendto_txt2img, llm_sendto_img2img
                ]

    # def process(self, p: StableDiffusionProcessingTxt2Img,*args):

    def process(self, p: StableDiffusionProcessingTxt2Img,
                llm_is_enabled, llm_recursive_use, llm_keep_your_prompt_use,
                llm_system_prompt, llm_ur_prompt,
                # llm_llm_answer,
                # llm_history,
                llm_max_token, llm_tempture,
                llm_apiurl, llm_apikey, llm_api_model_name,
                llm_api_translate_system_prompt, llm_api_translate_enabled,
                llm_is_open_eye,
                # llm_is_open_eye_last_one_image,
                llm_system_prompt_eye, llm_ur_prompt_eye, llm_ur_prompt_image_eye,
                llm_tempture_eye,
                # llm_llm_answer_eye,
                llm_max_token_eye,
                # llm_history_eye,
                # llm_sendto_txt2img, llm_sendto_img2img
                ):

        if llm_is_enabled:
            r = self.call_llm_pythonlib(llm_apiurl, llm_apikey, llm_api_model_name, llm_system_prompt, llm_ur_prompt,
                                        llm_max_token, llm_tempture,
                                        llm_recursive_use, llm_keep_your_prompt_use, llm_api_translate_system_prompt,
                                        llm_api_translate_enabled)
            g_result = str(r[0])

            # g_result += g_result+"\n\n"+translate_r
            for i in range(len(p.all_prompts)):
                p.all_prompts[i] = p.all_prompts[i] + (",\n" if (p.all_prompts[0].__len__() > 0) else "\n") + g_result

        if llm_is_open_eye:
            r2 = self.call_llm_eye_open(llm_apiurl, llm_apikey, llm_api_model_name, llm_system_prompt_eye,
                                        llm_ur_prompt_eye,
                                        llm_ur_prompt_image_eye, llm_tempture_eye,
                                        llm_max_token_eye, llm_api_translate_system_prompt,
                                        llm_api_translate_enabled)
            g_result2 = str(r2[0])
            for i in range(len(p.all_prompts)):
                p.all_prompts[i] = p.all_prompts[i] + (",\n" if (p.all_prompts[0].__len__() > 0) else "\n") + g_result2

        return p.all_prompts[0]

# with gr.Row():
#    js_neg_prompt_js = gr.Textbox(label="[Negative prompt-JS]", lines=3, value="{}")
#    js_neg_result = gr.Textbox(label="[Negative prompt-JS-Result]", lines=3, value="result")
#    # self.p.change(self.process, inputs=js_result, outputs=js_result)
# with gr.Row():
#     llm_models = gr.Dropdown(
#         ['noDetect'].append(List_LLM_Models), value=['noDetect'], multiselect=False,
#         label="List LLM "
#               "Models",
#         info="get models from local LLM. (:LM Studio)"
#     )

# script_callbacks.on_ui_tabs(on_ui_tabs)
