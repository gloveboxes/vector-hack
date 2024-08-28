from ollama import Client
import json

remote_host = "http://jumbo:11434"


def summarize_text(text: str):
    count = 0
    model = "phi3.5:3.8b-mini-instruct-q8_0"
    custom_client = Client(host=remote_host, timeout=60)

    master = json.load(open("master_enriched.json"))

    for r in master:
        text = r["text"]
        count += 1
        print(count)

        ollama_response = custom_client.chat(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You're an AI Assistant for video transcripts. Write a 60 word technical summary. Avoid starting sentences with 'This video'. Just give the summary in plain text, no additional information",
                },
                {
                    "role": "user",
                    "content": text,
                },
            ],
        )
        ollama_response = ollama_response["message"]["content"].strip()
        print(ollama_response)
        print("vs gpt-4o")
        print(r["summary".strip()])


if __name__ == "__main__":
    summarize_text("summarize in 20 words The quick brown fox jumps over the lazy dog.")
