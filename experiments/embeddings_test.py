from sentence_transformers import SentenceTransformer

MODEL_NAME = "all-MiniLM-L6-v2"

SENTENCES = [
    "The cat sat on the mat.",
    "A feline rested on the rug.",
    "The stock market crashed today.",
    "Investors panicked as prices fell.",
]


def main():
    model = SentenceTransformer(MODEL_NAME)
    embeddings = model.encode(SENTENCES)

    print(f"Shape: {embeddings.shape}")
    print(f"Dimension: {embeddings.shape[1]}")
    print()

    for i, sentence in enumerate(SENTENCES):
        print(f"Sentence {i + 1}: {sentence}")
        print(f"First 5 values: {embeddings[i][:5]}")
        print()


if __name__ == "__main__":
    main()
