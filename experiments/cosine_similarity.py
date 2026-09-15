from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

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

    similarity_matrix = cosine_similarity(embeddings)

    print("Cosine similarity between all pairs:\n")
    for i in range(len(SENTENCES)):
        for j in range(i + 1, len(SENTENCES)):
            score = similarity_matrix[i][j]
            print(f"Sentence {i + 1} vs Sentence {j + 1}: {score:.2f}")

    print()
    print(
        "Highest scores should be 1&2 (both about a cat on a surface) and 3&4 "
        "(both about a market crash). Cross-topic pairs like 1&3 or 2&4 should "
        "score much lower because the model places unrelated topics far apart "
        "in embedding space."
    )


if __name__ == "__main__":
    main()
