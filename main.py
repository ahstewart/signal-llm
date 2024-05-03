import sys
import tomli
import os
import datetime
from tqdm import tqdm
import sentencepiece as spm


class Chat:
    def __init__(self, chat_path, chat_name):
        self.chat_dir = f"{chat_path}/{chat_name}"
        self.chat_name = chat_name
        with open(f"{self.chat_dir}/index.md", "r", encoding="UTF-8") as chat_md:
            self.chat_text = chat_md.readlines()
        self.messages = []
        self.chat_text_cleaned = []
        self.convos = []
        self.members = []
        self.prompts = []

    def clean_text(self, media_excl):
        # remove all reactions
        self.chat_text_cleaned = [i for i in self.chat_text if i[:2] != '(-']
        # parse messages into a JSON-like list of dictionaries with following attributes -
        # timestamp, sender, message,
        print(f'Parsing {len(self.chat_text_cleaned)} messages from group chat "{self.chat_name}"...')
        for i in tqdm(range(len(self.chat_text_cleaned))):
            chat = self.chat_text_cleaned[i]
            if chat[0] == "[":
                raw_time = chat.split("]")[0][1:]
                year = raw_time.split("-")[0]
                month = raw_time.split("-")[1]
                day = raw_time.split("-")[2].split(" ")[0]
                hour = raw_time.split("-")[2].split(" ")[1].split(":")[0]
                minute = raw_time.split("-")[2].split(" ")[1].split(":")[1]
                timestamp = datetime.datetime(int(year), int(month), int(day), int(hour), int(minute))
                sender = chat.split("]")[1].split(":")[0][1:]
                text = " ".join(chat.split(":")[2:])[1:]
                reply = None
                # check if message was a reply
                if text == "\n":
                    text = self.chat_text_cleaned[i+4]
                    reply = self.chat_text_cleaned[i+2][2:]
                # check if message is from Nick AI
                if text[0].encode() == b'\xf0\x9f\xa4\x96':
                    sender = "NickAI"
                # check if message contains media, if it doesn't, write it
                if not any(ex in text for ex in media_excl):
                    # check if sender is same as last sender
                    if (i != 0) and (sender == self.messages[-1]['sender']):
                        self.messages[-1]['text'] = f"{self.messages[-1]['text']}\n{text}"
                    else:
                        self.messages.append({"timestamp": timestamp,
                                              "sender": sender,
                                              "text": text,
                                              "reply": reply})
                # add member to member list
                if sender not in self.members:
                    self.members.append(sender)

    def generate_conversations(self, message_list, convo_threshold):
        # initialize tokenizer
        sp = spm.SentencePieceProcessor()
        print(sp.encode("this is some text"))
        # group messages into conversations based on convo_dropoff time
        last_index = 0
        for m in range(len(message_list)):
            if m != 0:
                time1 = message_list[m-1]["timestamp"]
                time2 = message_list[m]["timestamp"]
                diff = time2 - time1
                if diff >= datetime.timedelta(hours=convo_threshold):

                    self.convos.append(message_list[last_index:m])
                    last_index = m

    def generate_prompts(self, prompt_template):
        print("\nTurning messages into prompts...\n")
        for c in tqdm(self.convos):
            prompt = ""
            for ms in range(1, len(c)):
                prompt = ""
                for msgs in range(ms+1):
                    mems = [people for people in self.members if people != c[ms]["sender"]]
                    system_prompt = prompt_template.format(c[ms]["sender"], mems)
                    rootSender = c[ms]['sender']
                    iterSender = c[msgs]['sender']
                    if prompt == "":
                        if rootSender == iterSender:
                            if ms == msgs:
                                prompt = f"<s> [INST] <<SYS>> {system_prompt} <</SYS>> \n\n " \
                                         f"{c[msgs-1]['sender']}: {c[msgs-1]['text']} [/INST] \n " \
                                         f"{iterSender}: {c[msgs]['text']} </s> \n"
                            else:
                                prompt = f"<s> [INST] <<SYS>> {system_prompt} <</SYS>> \n\n " \
                                         f"{c[msgs-1]['sender']}: {c[msgs-1]['text']} [/INST] \n " \
                                         f"{iterSender}: {c[msgs]['text']} </s> \n <s> [INST]"
                        else:
                            prompt = f"<s> [INST] <<SYS>> {system_prompt} <</SYS>> \n\n " \
                                     f"{c[msgs-1]['sender']}: {c[msgs-1]['text']} \n " \
                                     f"{iterSender}: {c[msgs]['text']}"
                    else:
                        if rootSender == iterSender:
                            if ms == msgs:
                                prompt = f"{prompt} [/INST] \n " \
                                         f"{iterSender}: {c[msgs]['text']} </s> \n"
                            else:
                                prompt = f"{prompt} [/INST] \n " \
                                         f"{iterSender}: {c[msgs]['text']} </s> \n <s> [INST]"
                        else:
                            prompt = f"{prompt} \n " \
                                     f"{iterSender}: {c[msgs]['text']} \n "
                self.prompts.append(prompt)


if __name__ == "__main__":
    # try to load config file
    cwd = os.getcwd()
    config_name = "config.toml"
    try:
        with open(f"{cwd}/{config_name}", "rb") as f:
            config_dict = tomli.load(f)
    except tomli.TOMLDecodeError:
        print("Not a valid config file format.")
        sys.exit()

    # create Chat object and get text from markdown file
    chat1 = Chat(config_dict["chat_path"], config_dict["chat_name"])
    chat1.clean_text(config_dict["media_exclusions"])
    txt = chat1.chat_text
    text_cleaned = chat1.chat_text_cleaned
    messages = chat1.messages
    chat1.generate_conversations(messages, config_dict["convo_dropoff"])
    chat1.generate_prompts(config_dict['system_prompt_template'])