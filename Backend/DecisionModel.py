import ollama


def askLLM(query : str) -> str:
    response = ollama.generate(model="tinyllama", prompt=query)
    return response["response"]

if __name__ == "__main__":
    print (askLLM(""))
