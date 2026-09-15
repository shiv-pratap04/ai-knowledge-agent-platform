from langchain_huggingface import HuggingFaceEmbeddings

embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
vector = embeddings.embed_query("The cat sat on the mat.")
print("dimension:", len(vector))
print("first 5:", vector[:5])
