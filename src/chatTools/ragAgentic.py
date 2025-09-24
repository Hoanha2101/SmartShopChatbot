import os
import chromadb
from chromadb.config import Settings
from langchain.text_splitter import RecursiveCharacterTextSplitter, CharacterTextSplitter
import shutil
from ..models import model_emb 

class RAG:
    _instance = None
    
    def __init__(self, 
                 base_db_folder: str = "database/rag",
                 db_name: str = "rag_db",
                 chroma_path: str = None,  # Mặc định sẽ tự động tạo
                 
                 separator="\n",    
                 chunk_size=500,  
                 chunk_overlap=50, 
                 length_function=len
                 ):
        
        self.separator = separator
        self.chunk_size = chunk_size  
        self.chunk_overlap = chunk_overlap 
        self.length_function = length_function
        
        self.base_db_folder = base_db_folder
        self.db_name = db_name
        
        # Tự động tạo đường dẫn nếu không được cung cấp
        if chroma_path is None:
            self.chroma_path = os.path.join(os.getcwd(), "database", "chroma_db")
        else:
            self.chroma_path = chroma_path
            
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        # Tạo thư mục nếu chưa tồn tại
        os.makedirs(self.chroma_path, exist_ok=True)
        
        # init chroma client
        self.client = chromadb.PersistentClient(path=self.chroma_path)
        self.collection = self.client.get_or_create_collection(name=self.db_name)
        
        print(f"💾 ChromaDB được lưu tại: {os.path.abspath(self.chroma_path)}")

    def load_file(self, file_path: str) -> str:
        """Đọc toàn bộ file txt"""
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    def split_chunk(self, text: str):
        """Chia text thành chunks với RecursiveCharacterTextSplitter"""
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", " ", ""]
        )
        
        # text_splitter = CharacterTextSplitter(
        #     separator=self.separator,     
        #     chunk_size=self.chunk_size,   
        #     chunk_overlap=self.chunk_overlap,  
        #     length_function=self.length_function 
        # )
        
        chunks = text_splitter.split_text(text)
        return chunks

    def add_to_db(self, file_path: str):
        """Đọc file, split chunk và add vào ChromaDB"""
        text = self.load_file(file_path)
        chunks = self.split_chunk(text)

        file_name = os.path.basename(file_path)
        rel_path = os.path.relpath(file_path, os.path.dirname(file_path))
        file_prefix = file_name.replace('.', '_')

        for i, chunk in enumerate(chunks):
            emb = model_emb.encode(chunk).tolist()
            self.collection.add(
                documents=[chunk],
                embeddings=[emb],
                ids=[f"{file_prefix}_{i}"],
                metadatas=[{
                    'file_path': file_path,
                    'file_name': file_name,
                    'chunk_index': i,
                    'relative_path': rel_path
                }]
            )
        print(f"✅ Đã thêm {len(chunks)} chunks từ {file_path} vào ChromaDB")


    def add_folder_to_db(self, folder_path: str, file_extensions: list = ['.txt', '.md', '.py', '.json']):
        """Đọc tất cả files trong folder và add vào ChromaDB"""
        if not os.path.exists(folder_path):
            print(f"❌ Folder không tồn tại: {folder_path}")
            return
        
        total_files = 0
        total_chunks = 0
        
        # Duyệt qua tất cả files trong folder (bao gồm cả subfolder)
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                # Kiểm tra extension của file
                file_ext = os.path.splitext(file)[1].lower()
                if file_ext in file_extensions:
                    file_path = os.path.join(root, file)
                    
                    try:
                        # Đọc và xử lý file
                        text = self.load_file(file_path)
                        chunks = self.split_chunk(text)
                        
                        # Tạo relative path để làm prefix cho ID
                        rel_path = os.path.relpath(file_path, folder_path)
                        file_prefix = rel_path.replace(os.sep, '_').replace('.', '_')
                        
                        # Add chunks vào database
                        for i, chunk in enumerate(chunks):
                            emb = model_emb.encode(chunk).tolist()
                            self.collection.add(
                                documents=[chunk],
                                embeddings=[emb],
                                ids=[f"{file_prefix}_{i}"],
                                metadatas=[{
                                    'file_path': file_path,
                                    'file_name': file,
                                    'chunk_index': i,
                                    'relative_path': rel_path
                                }]
                            )
                        
                        total_files += 1
                        total_chunks += len(chunks)
                        print(f"✅ Đã xử lý: {rel_path} - {len(chunks)} chunks")
                        
                    except Exception as e:
                        print(f"❌ Lỗi khi xử lý file {file_path}: {str(e)}")
                        continue
        
        print(f"🎉 Hoàn thành! Đã xử lý {total_files} files với tổng {total_chunks} chunks")

    def add_data(self, path: str, file_extensions: list = ['.txt', '.md', '.py', '.json']):
        """Method tổng quát để add file hoặc folder"""
        if os.path.isfile(path):
            # Nếu là file đơn
            self.add_to_db(path)
        elif os.path.isdir(path):
            # Nếu là folder
            self.add_folder_to_db(path, file_extensions)
        else:
            print(f"❌ Path không hợp lệ: {path}")

    def search(self, query: str, top_k: int = 3):
        """Tìm kiếm theo query"""
        q_emb = model_emb.encode(query).tolist()
        results = self.collection.query(
            query_embeddings=[q_emb],
            n_results=top_k,
            include=["embeddings", "documents", "metadatas", "distances"] # Mặc định sẽ ko lấy ra emb luôn, phải set thì mới lấy ra.
        )
        
        return results["documents"]
    
    def search_with_neighbors(self, query: str, top_k: int = 3, return_docs_only: bool = True):
        """Tìm kiếm query, lấy thêm chunk trước & sau mỗi kết quả.
        Nếu return_docs_only=True thì trả ra list document thôi."""
        q_emb = model_emb.encode(query).tolist()
        results = self.collection.query(
            query_embeddings=[q_emb],
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )

        final_results = []

        for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
            file_path = meta["file_path"]
            rel_path = meta["relative_path"]
            chunk_index = meta["chunk_index"]
            chunk_id = meta.get("chunk_id", f"{rel_path}_{chunk_index}")

            # lấy toàn bộ chunks trong file này
            file_chunks = self.collection.get(
                where={"relative_path": rel_path},
                include=["documents", "metadatas"]
            )

            # map index -> content
            chunks_map = {
                m["chunk_index"]: d
                for d, m in zip(file_chunks["documents"], file_chunks["metadatas"])
            }

            # lấy [index-1, index, index+1]
            neighbors = []
            for i in [chunk_index - 1, chunk_index, chunk_index + 1]:
                if i in chunks_map:
                    neighbors.append({
                        "chunk_index": i,
                        "document": chunks_map[i],
                        "file_path": file_path,
                        "relative_path": rel_path
                    })

            final_results.append({
                "match_id": chunk_id,
                "neighbors": neighbors
            })

        if return_docs_only:
            # gộp tất cả document lại thành 1 list text
            docs = []
            for item in final_results:
                for n in item["neighbors"]:
                    docs.append(n["document"])
            return docs

        return final_results



    def search_with_metadata(self, query: str, top_k: int = 3):
        """Tìm kiếm kèm metadata để biết chunk từ file nào"""
        q_emb = model_emb.encode(query).tolist()
        results = self.collection.query(
            query_embeddings=[q_emb],
            n_results=top_k
        )

        return {
            "documents": results["documents"][0],
            "metadatas": results["metadatas"][0],
            "ids": results["ids"][0],
            "distances": results["distances"][0]
        }
        
    # Trả về cả documents và metadata
    def get_db_info(self):
        """Hiển thị thông tin về database"""
        print(f"📍 Database path: {os.path.abspath(self.chroma_path)}")
        print(f"📊 Database name: {self.db_name}")
        print(f"📁 Collections: {[col.name for col in self.client.list_collections()]}")
        print(f"📈 Total documents: {self.collection.count()}")
        
        # Liệt kê files trong database folder
        if os.path.exists(self.chroma_path):
            files = os.listdir(self.chroma_path)
            print(f"📂 Files in database folder: {files}")
        
        return {
            'path': os.path.abspath(self.chroma_path),
            'name': self.db_name,
            'collections': [col.name for col in self.client.list_collections()],
            'document_count': self.collection.count()
        }
    
    def clear_database(self):
        """Xóa toàn bộ database (collection + file lưu trữ)"""
        try:
            # Xóa collection trong client
            self.client.delete_collection(self.db_name)
            print(f"🗑️ Đã xóa collection '{self.db_name}' trong client")

            # Xóa thư mục vật lý chứa DB
            if os.path.exists(self.chroma_path):
                shutil.rmtree(self.chroma_path)
                print(f"🗑️ Đã xóa toàn bộ database folder: {self.chroma_path}")

            # Tạo lại thư mục rỗng để dùng tiếp
            os.makedirs(self.chroma_path, exist_ok=True)
            self.client = chromadb.PersistentClient(path=self.chroma_path)
            self.collection = self.client.get_or_create_collection(name=self.db_name)
            print("✅ Database đã được reset mới hoàn toàn")

        except Exception as e:
            print(f"❌ Lỗi khi xóa database: {e}")
        
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance