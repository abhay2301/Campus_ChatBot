# test_index.py
import pickle

with open("vector_index/faiss_index.pkl", "rb") as f:
    data = pickle.load(f)
    
print(f"Questions: {len(data['questions'])}")
print(f"Answers: {len(data['answers'])}")
print(f"Model: {data.get('model_name', 'all-MiniLM-L6-v2')}")
print("Sample QA:")
for i in range(min(3, len(data['questions']))):
    print(f"Q: {data['questions'][i]}")
    print(f"A: {data['answers'][i]}")
    print()