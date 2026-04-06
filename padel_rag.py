"""
Système RAG (Retrieval Augmented Generation) pour les livres de padel
Indexe et recherche dans les connaissances des livres PDF
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Optional
import chromadb
from chromadb.config import Settings
import PyPDF2
import re


class PadelRAG:
    """
    Système RAG pour enrichir l'IA avec les connaissances des livres de padel
    """
    
    def __init__(self, db_path: str = "data/chroma_db", collection_name: str = "padel_books"):
        """
        Initialise le système RAG
        
        Args:
            db_path: Chemin vers la base ChromaDB
            collection_name: Nom de la collection ChromaDB
        """
        self.db_path = Path(db_path)
        self.db_path.mkdir(parents=True, exist_ok=True)
        
        # Initialiser ChromaDB
        self.client = chromadb.PersistentClient(
            path=str(self.db_path),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Créer ou récupérer la collection
        try:
            self.collection = self.client.get_collection(name=collection_name)
            print(f"Collection '{collection_name}' chargée ({self.collection.count()} chunks)")
        except:
            self.collection = self.client.create_collection(
                name=collection_name,
                metadata={"description": "Connaissances des livres de padel"}
            )
            print(f"Nouvelle collection '{collection_name}' créée")
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """
        Extrait le texte d'un fichier PDF
        
        Args:
            pdf_path: Chemin vers le fichier PDF
            
        Returns:
            Texte extrait du PDF
        """
        text = ""
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                total_pages = len(pdf_reader.pages)
                
                print(f"Extraction de {total_pages} pages depuis {Path(pdf_path).name}...")
                
                for page_num in range(total_pages):
                    page = pdf_reader.pages[page_num]
                    text += page.extract_text() + "\n"
                    
                    if (page_num + 1) % 10 == 0:
                        print(f"  ... {page_num + 1}/{total_pages} pages extraites")
                
                print(f"OK - {total_pages} pages extraites ({len(text)} caractères)")
                
        except Exception as e:
            print(f"ERREUR - Impossible d'extraire le PDF {pdf_path}: {e}")
        
        return text
    
    def chunk_text(self, text: str, chunk_size: int = 800, overlap: int = 100) -> List[str]:
        """
        Découpe le texte en chunks avec chevauchement
        
        Args:
            text: Texte à découper
            chunk_size: Taille des chunks en caractères
            overlap: Chevauchement entre chunks
            
        Returns:
            Liste de chunks de texte
        """
        # Nettoyer le texte
        text = re.sub(r'\s+', ' ', text)  # Normaliser les espaces
        text = text.strip()
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # Si on n'est pas à la fin, essayer de couper à un point, une virgule ou un espace
            if end < len(text):
                # Chercher le dernier point ou virgule
                cut_point = max(
                    text.rfind('.', start, end),
                    text.rfind('!', start, end),
                    text.rfind('?', start, end),
                    text.rfind('\n', start, end)
                )
                
                # Si pas trouvé, chercher un espace
                if cut_point <= start:
                    cut_point = text.rfind(' ', start, end)
                
                # Si toujours pas trouvé, couper à la taille exacte
                if cut_point <= start:
                    cut_point = end
                
                end = cut_point + 1
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # Avancer avec chevauchement
            start = end - overlap
        
        return chunks
    
    def index_pdf(self, pdf_path: str, book_name: Optional[str] = None):
        """
        Indexe un fichier PDF dans ChromaDB
        
        Args:
            pdf_path: Chemin vers le fichier PDF
            book_name: Nom du livre (optionnel, sinon utilise le nom du fichier)
        """
        if book_name is None:
            book_name = Path(pdf_path).stem
        
        print(f"\n{'='*60}")
        print(f"INDEXATION: {book_name}")
        print(f"{'='*60}")
        
        # Extraire le texte
        text = self.extract_text_from_pdf(pdf_path)
        
        if not text:
            print("ATTENTION - Aucun texte extrait du PDF")
            return
        
        # Découper en chunks
        chunks = self.chunk_text(text, chunk_size=800, overlap=100)
        print(f"OK - {len(chunks)} chunks créés")
        
        # Préparer les données pour ChromaDB
        ids = []
        documents = []
        metadatas = []
        
        for i, chunk in enumerate(chunks):
            chunk_id = f"{book_name}_chunk_{i}"
            ids.append(chunk_id)
            documents.append(chunk)
            metadatas.append({
                "book": book_name,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "source": Path(pdf_path).name
            })
        
        # Ajouter à ChromaDB (par batch de 100)
        batch_size = 100
        total_batches = (len(ids) + batch_size - 1) // batch_size
        
        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, len(ids))
            
            self.collection.add(
                ids=ids[start_idx:end_idx],
                documents=documents[start_idx:end_idx],
                metadatas=metadatas[start_idx:end_idx]
            )
            
            print(f"  ... Batch {batch_num + 1}/{total_batches} indexé")
        
        print(f"OK - {len(chunks)} chunks indexés pour '{book_name}'")
        print(f"Total dans la collection: {self.collection.count()} chunks")
    
    def index_all_pdfs(self, books_dir: str = "data/books"):
        """
        Indexe tous les PDFs d'un dossier
        
        Args:
            books_dir: Dossier contenant les PDFs
        """
        books_path = Path(books_dir)
        
        if not books_path.exists():
            print(f"ERREUR - Dossier non trouvé: {books_dir}")
            return
        
        pdf_files = list(books_path.glob("*.pdf"))
        
        if not pdf_files:
            print(f"ATTENTION - Aucun fichier PDF trouvé dans {books_dir}")
            return
        
        print(f"\n{'='*60}")
        print(f"INDEXATION DE {len(pdf_files)} LIVRE(S)")
        print(f"{'='*60}")
        
        for pdf_file in pdf_files:
            self.index_pdf(str(pdf_file))
        
        print(f"\n{'='*60}")
        print(f"INDEXATION TERMINÉE")
        print(f"Total: {self.collection.count()} chunks dans la base")
        print(f"{'='*60}\n")
    
    def search(self, query: str, n_results: int = 5) -> List[Dict]:
        """
        Recherche les chunks les plus pertinents
        
        Args:
            query: Question ou requête
            n_results: Nombre de résultats à retourner
            
        Returns:
            Liste de dictionnaires avec les chunks trouvés
        """
        if self.collection.count() == 0:
            print("ATTENTION - La base de connaissances est vide. Indexez d'abord vos livres.")
            return []
        
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results
        )
        
        # Formater les résultats
        formatted_results = []
        
        if results['documents'] and results['documents'][0]:
            for i in range(len(results['documents'][0])):
                formatted_results.append({
                    'text': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i] if 'distances' in results else None
                })
        
        return formatted_results
    
    def get_context_for_query(self, query: str, n_results: int = 3) -> str:
        """
        Récupère le contexte pertinent pour une question
        
        Args:
            query: Question
            n_results: Nombre de chunks à récupérer
            
        Returns:
            Contexte formaté pour injection dans le prompt
        """
        results = self.search(query, n_results=n_results)
        
        if not results:
            return ""
        
        context_parts = []
        context_parts.append("=== CONNAISSANCES DES LIVRES DE PADEL ===\n")
        
        for i, result in enumerate(results, 1):
            book_name = result['metadata'].get('book', 'Inconnu')
            text = result['text']
            
            context_parts.append(f"[Livre: {book_name}]")
            context_parts.append(text)
            context_parts.append("")  # Ligne vide
        
        context_parts.append("=== FIN DES CONNAISSANCES ===\n")
        
        return "\n".join(context_parts)
    
    def reset(self):
        """Réinitialise complètement la base de données"""
        try:
            self.client.delete_collection(self.collection.name)
            print("Collection supprimée avec succès")
        except:
            pass
        
        # Recréer la collection
        self.collection = self.client.create_collection(
            name=self.collection.name,
            metadata={"description": "Connaissances des livres de padel"}
        )
        print("Nouvelle collection créée")
    
    def get_stats(self) -> Dict:
        """Retourne les statistiques de la base"""
        total_chunks = self.collection.count()
        
        # Récupérer tous les métadonnées pour compter les livres
        if total_chunks > 0:
            all_data = self.collection.get()
            books = set(meta.get('book', 'Inconnu') for meta in all_data['metadatas'])
        else:
            books = set()
        
        return {
            'total_chunks': total_chunks,
            'total_books': len(books),
            'books': sorted(list(books))
        }


def main():
    """Fonction principale pour tester le système RAG"""
    import sys
    
    rag = PadelRAG()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "index":
            # Indexer tous les PDFs du dossier data/books
            rag.index_all_pdfs()
        
        elif command == "reset":
            # Réinitialiser la base
            confirm = input("Voulez-vous vraiment supprimer toute la base ? (oui/non): ")
            if confirm.lower() == "oui":
                rag.reset()
                print("Base réinitialisée")
        
        elif command == "stats":
            # Afficher les statistiques
            stats = rag.get_stats()
            print(f"\n{'='*60}")
            print("STATISTIQUES DE LA BASE RAG")
            print(f"{'='*60}")
            print(f"Nombre de livres indexés: {stats['total_books']}")
            print(f"Nombre total de chunks: {stats['total_chunks']}")
            if stats['books']:
                print(f"\nLivres:")
                for book in stats['books']:
                    print(f"  - {book}")
            print(f"{'='*60}\n")
        
        elif command == "search":
            # Rechercher
            if len(sys.argv) > 2:
                query = " ".join(sys.argv[2:])
                print(f"\nRecherche: {query}\n")
                
                results = rag.search(query, n_results=3)
                
                for i, result in enumerate(results, 1):
                    print(f"\n{'='*60}")
                    print(f"RÉSULTAT {i}")
                    print(f"Livre: {result['metadata']['book']}")
                    print(f"Chunk: {result['metadata']['chunk_index']}/{result['metadata']['total_chunks']}")
                    if result['distance']:
                        print(f"Score: {result['distance']:.4f}")
                    print(f"{'='*60}")
                    print(result['text'])
            else:
                print("Usage: python padel_rag.py search <votre question>")
        
        else:
            print(f"Commande inconnue: {command}")
    
    else:
        print("""
Système RAG pour les livres de padel

Usage:
  python padel_rag.py index          # Indexer tous les PDFs de data/books/
  python padel_rag.py stats          # Afficher les statistiques
  python padel_rag.py search <query> # Rechercher dans la base
  python padel_rag.py reset          # Réinitialiser la base

Exemples:
  python padel_rag.py index
  python padel_rag.py search "Comment faire une bandeja"
  python padel_rag.py stats
        """)


if __name__ == "__main__":
    main()
