import os

from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings

MODEL_NAME = "models/text-embedding-004"

SENTENCES = [
    "The cat sat on the mat.",
    "A feline rested on the rug.",
    "The stock market crashed today.",
    "Investors panicked as prices fell.",
]


def main():
    load_dotenv()
    embeddings = GoogleGenerativeAIEmbeddings(
        model=MODEL_NAME,
        google_api_key=os.environ["GOOGLE_API_KEY"],
    ).embed_documents(SENTENCES)

    print(f"Shape: ({len(embeddings)}, {len(embeddings[0])})")
    print(f"Dimension: {len(embeddings[0])}")
    print()

    for i, sentence in enumerate(SENTENCES):
        print(f"Sentence {i + 1}: {sentence}")
        print(f"First 5 values: {embeddings[i][:5]}")
        print()


if __name__ == "__main__":
    main()
