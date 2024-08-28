from ollama import Client
import json

remote_host = "http://jumbo:11434"
custom_client = Client(host=remote_host, timeout=10)


def get_text_embedding(prompt: str):
    max_retry = 3

    for i in range(max_retry):
        try:
            embedding_result = custom_client.embeddings(model="nomic-embed-text", prompt=prompt)
            return embedding_result["embedding"]
        except Exception as e:
            print(f"Error: {e}")


def load_master():
    count = 0
    master = json.load(open("master_enriched.json"))
    for r in master:
        text = r["text"]
        count += 1
        print(count)

        r["ada_v2"] = {}

    with open("master_enriched.json", "w") as f:
        json.dump(master, f)

    count = 0

    for r in master:
        text = r["text"]
        count += 1
        print(count)

        result = get_text_embedding(text)
        # print(result)
        r["ada_v2"] = result

    with open("master_enriched.json", "w") as f:
        json.dump(master, f)


if __name__ == "__main__":
    load_master()
