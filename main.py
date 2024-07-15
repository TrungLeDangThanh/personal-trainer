from openai import OpenAI
from dotenv import find_dotenv, load_dotenv
from time import strftime, gmtime, sleep
from json import load, dump
import streamlit as st
import os
import logging


class Caching:
    @staticmethod
    def create_file_if_not_exists(filepath):
        dir_path = os.path.dirname(filepath)

        try:
            os.makedirs(dir_path)
        except FileExistsError:
            pass
            
        try:
            with open(filepath, "x"):
                pass
        except FileExistsError:
            pass

    @staticmethod
    def load_from_cache(filepath):
        try:
            with open(filepath, "r") as cache:
                data = load(cache)
            return data
        except (FileNotFoundError, ValueError):
            return None
        
    @staticmethod
    def save_to_cache(filepath, assistant_id, thread_id):
        Caching.create_file_if_not_exists(filepath)

        data = {
            "assistant_id": assistant_id,
            "thread_id": thread_id
        }
        
        with open (filepath, "w") as cache:
            dump(data, cache)


cache_file_path = "./temp/cache.json"
log_file_path = "./temp/log.log"

Caching.create_file_if_not_exists(log_file_path)
logging.basicConfig(level=logging.INFO, filename=log_file_path, filemode="a",
                    format="%(asctime)s - %(levelname)s - %(message)s")

dotenv_path = find_dotenv()
load_dotenv(dotenv_path)

client = OpenAI()
client.api_key = os.environ.get("OPENAI_API_KEY")

model = "gpt-3.5-turbo"
name = "Personal Trainer"
instructions = """
You are Jeff, the best personal trainer and nutritionist who knows how to get clients to build lean muscles.
You've trained high-caliber athletes and movie stars.
Your task is to answer any questions from the user about health, diet, workout, and lifestyle, and give them advice.
Please address the user as Trung.
"""


class AssistantManager:
    assistant_id = None
    thread_id = None

    def __init__(self):
        self.client = client
        self.assistant = None
        self.thread = None
        self.run = None
        self.response = None
        self.runtime = None

        data = Caching.load_from_cache(cache_file_path)

        try:
            AssistantManager.assistant_id = data["assistant_id"]
        except (TypeError, KeyError):
            pass

        try:
            AssistantManager.thread_id = data["thread_id"]
        except (TypeError, KeyError):
            pass

        if AssistantManager.assistant_id:
            try:
                logging.info("Assistant ID exists. Retrieving Assistant...")
                self.assistant = self.client.beta.assistants.retrieve(
                    assistant_id=AssistantManager.assistant_id
                )
                logging.info("Assistant retrieved successfully")
                logging.info(f"Current Assistant ID is: {AssistantManager.assistant_id}")
            except Exception as e:
                logging.error(f"Fail to retrieve Assistant: {e}")
                logging.info("No Assistant found. Creating new Assistant...")
                self.create_assistant()
        else:
            logging.info("Assistant ID not found. Creating new Assistant...")
            self.create_assistant()

        if AssistantManager.thread_id:
            try:
                logging.info("Thread ID exists. Retrieving Thread...")
                self.thread = self.client.beta.threads.retrieve(
                    thread_id=AssistantManager.thread_id
                )
                logging.info("Thread retrieved successfully")
                logging.info(f"Current Thread ID is: {AssistantManager.thread_id}")
            except Exception as e:
                logging.error(f"Fail to retrieve Thread: {e}")
                logging.info("No Thread found. Creating new Thread...")
                self.create_thread()
        else:
            logging.info("Thread ID not found. Creating new Thread...")
            self.create_thread()

    def create_assistant(self):
        self.assistant = self.client.beta.assistants.create(
            name=name,
            instructions=instructions,
            model=model
        )
        AssistantManager.assistant_id = self.assistant.id
        logging.info(f"New Assistant has been created, ID is: {AssistantManager.assistant_id}")
        Caching.save_to_cache(cache_file_path, AssistantManager.assistant_id, AssistantManager.thread_id)

    def create_thread(self):
        self.thread = self.client.beta.threads.create()
        AssistantManager.thread_id = self.thread.id
        logging.info(f"New Thread has been created, ID is: {AssistantManager.thread_id}")
        Caching.save_to_cache(cache_file_path, AssistantManager.assistant_id, AssistantManager.thread_id)

    def ask_assistant(self, message):
        self.client.beta.threads.messages.create(
            thread_id=AssistantManager.thread_id,
            role="user",
            content=message
        )

    def run_assistant(self):
        self.run = self.client.beta.threads.runs.create(
            assistant_id=AssistantManager.assistant_id,
            thread_id=AssistantManager.thread_id,
            instructions=instructions
        )
        self.run_id = self.run.id

    def wait_assistant(self):
        sleep_interval = 1
        timeout = 20

        while True:
            try:
                self.run = self.client.beta.threads.runs.retrieve(
                    thread_id=AssistantManager.thread_id,
                    run_id=self.run_id,
                    timeout=timeout
                )

                if self.run.status == "completed":
                    self.retrieve_response()
                    self.retrieve_runtime()
                    break
                else:
                    logging.info("Waiting for Run to complete...")
                    sleep(sleep_interval)

            except Exception as e:
                logging.error(f"Error occurred while retrieving the Run: {e}")
                break

    def retrieve_response(self):
        messages = self.client.beta.threads.messages.list(
            thread_id=AssistantManager.thread_id,
            run_id=self.run_id
        )

        last_message = messages.data[0]
        response = last_message.content[0].text.value
        self.response = response

    def retrieve_runtime(self):
        elapsed_time = self.run.completed_at - self.run.created_at
        formatted_elapsed_time = strftime(
            "%H:%M:%S",
            gmtime(elapsed_time)
        )

        logging.info(f"Run completed in: {formatted_elapsed_time}")
        self.runtime = formatted_elapsed_time

    def return_response(self):
        return self.response
    
    def return_runtime(self):
        return self.runtime


class Streamlit:
    @staticmethod
    def streamlit():
        st.title("Personal Trainer")

        with st.form("my_form"):
            message = st.text_input("Ask me anything")
            submit = st.form_submit_button("Send")

            if submit:
                manager = AssistantManager()
                
                manager.ask_assistant(message)
                manager.run_assistant()
                manager.wait_assistant()

                response = manager.return_response()
                runtime = manager.return_runtime()

                st.write(response)
                st.code(f"Time taken: {runtime}")


Streamlit.streamlit()

# manager = AssistantManager()
# message = input("Ask me anything: ")

# manager.ask_assistant(message)
# manager.run_assistant()
# manager.wait_assistant()

# response = manager.return_response()
# runtime = manager.return_runtime()

# print(response)
# print(f"Time taken: {runtime}")
