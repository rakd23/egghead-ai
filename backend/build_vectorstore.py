from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from dotenv import load_dotenv

load_dotenv()

print("Loading documents from uc_davis_data/...")
loader = DirectoryLoader('uc_davis_data/', glob="**/*.txt", loader_cls=TextLoader)
documents = loader.load()

print(f"✓ Loaded {len(documents)} documents")

print("Splitting documents into chunks...")
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200
)
chunks = text_splitter.split_documents(documents)

print(f"✓ Split into {len(chunks)} chunks")

print("Creating vector database (this may take a minute)...")
embeddings = OpenAIEmbeddings()
vectorstore = FAISS.from_documents(
    documents=chunks,
    embedding=embeddings
)

# Save to disk
vectorstore.save_local("faiss_db")

print("✓ Vector store created successfully in ./faiss_db!")
print("\nYou can now use this database in your chatbot.")