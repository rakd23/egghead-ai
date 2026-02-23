from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from supabase import create_client, Client
from dotenv import load_dotenv
import os
import sys

# Force immediate output
sys.stdout.flush()

load_dotenv()

print("Step 1: Connecting to Supabase...", flush=True)

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

if not supabase_url or not supabase_key:
    print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env file")
    exit(1)

supabase: Client = create_client(supabase_url, supabase_key)
print("✓ Connected to Supabase", flush=True)

print("Step 2: Loading documents from uc_davis_data/...", flush=True)
loader = DirectoryLoader('uc_davis_data/', glob="**/*.txt", loader_cls=TextLoader)
documents = loader.load()
print(f"✓ Loaded {len(documents)} documents", flush=True)

print("Step 3: Splitting documents into chunks...", flush=True)
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200
)
chunks = text_splitter.split_documents(documents)
print(f"✓ Split into {len(chunks)} chunks", flush=True)

print("Step 4: Creating embeddings...", flush=True)
embeddings = OpenAIEmbeddings()
print("✓ Embeddings model loaded", flush=True)

print("Step 5: Uploading to Supabase (this will take a while)...", flush=True)

# Upload chunks one by one so we can see progress
for i, chunk in enumerate(chunks):
    print(f"  Uploading chunk {i+1}/{len(chunks)}...", flush=True)
    
    # Get embedding
    embedding = embeddings.embed_query(chunk.page_content)
    
    # Insert into Supabase
    supabase.table("documents").insert({
        "content": chunk.page_content,
        "metadata": chunk.metadata,
        "embedding": embedding
    }).execute()

print("✓ All chunks uploaded successfully!", flush=True)
print("\n🎉 Your teammates can now access this database!")