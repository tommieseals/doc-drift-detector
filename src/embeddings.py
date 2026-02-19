"""
Embeddings - Semantic similarity for fuzzy matching between code and docs.
Optional AI-powered component for detecting semantic drift.
"""

import hashlib
import json
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Tuple
from functools import lru_cache
import os


@dataclass
class EmbeddingResult:
    """Result of generating an embedding."""
    text: str
    embedding: List[float]
    model: str
    
    def similarity(self, other: 'EmbeddingResult') -> float:
        """Calculate cosine similarity with another embedding."""
        return cosine_similarity(self.embedding, other.embedding)


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    if len(vec1) != len(vec2):
        return 0.0
    
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = sum(a * a for a in vec1) ** 0.5
    norm2 = sum(b * b for b in vec2) ** 0.5
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return dot_product / (norm1 * norm2)


class EmbeddingProvider:
    """Base class for embedding providers."""
    
    def embed(self, text: str) -> EmbeddingResult:
        raise NotImplementedError
    
    def embed_batch(self, texts: List[str]) -> List[EmbeddingResult]:
        return [self.embed(text) for text in texts]


class OpenAIEmbeddings(EmbeddingProvider):
    """OpenAI embeddings using text-embedding-3-small."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get('OPENAI_API_KEY')
        self.model = "text-embedding-3-small"
        
        if not self.api_key:
            raise ValueError("OpenAI API key required. Set OPENAI_API_KEY environment variable.")
    
    def embed(self, text: str) -> EmbeddingResult:
        try:
            import openai
            client = openai.OpenAI(api_key=self.api_key)
            
            response = client.embeddings.create(
                input=text,
                model=self.model
            )
            
            return EmbeddingResult(
                text=text,
                embedding=response.data[0].embedding,
                model=self.model
            )
        except ImportError:
            raise ImportError("openai package required. Install with: pip install openai")
    
    def embed_batch(self, texts: List[str]) -> List[EmbeddingResult]:
        try:
            import openai
            client = openai.OpenAI(api_key=self.api_key)
            
            response = client.embeddings.create(
                input=texts,
                model=self.model
            )
            
            return [
                EmbeddingResult(
                    text=texts[i],
                    embedding=data.embedding,
                    model=self.model
                )
                for i, data in enumerate(response.data)
            ]
        except ImportError:
            raise ImportError("openai package required. Install with: pip install openai")


class LocalEmbeddings(EmbeddingProvider):
    """Local embeddings using sentence-transformers (no API needed)."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None
    
    @property
    def model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name)
            except ImportError:
                raise ImportError(
                    "sentence-transformers required. Install with: "
                    "pip install sentence-transformers"
                )
        return self._model
    
    def embed(self, text: str) -> EmbeddingResult:
        embedding = self.model.encode(text).tolist()
        return EmbeddingResult(
            text=text,
            embedding=embedding,
            model=self.model_name
        )
    
    def embed_batch(self, texts: List[str]) -> List[EmbeddingResult]:
        embeddings = self.model.encode(texts)
        return [
            EmbeddingResult(
                text=text,
                embedding=emb.tolist(),
                model=self.model_name
            )
            for text, emb in zip(texts, embeddings)
        ]


class SimpleEmbeddings(EmbeddingProvider):
    """Simple TF-IDF-like embeddings (no ML libraries required)."""
    
    def __init__(self, vocab_size: int = 1000):
        self.vocab_size = vocab_size
        self.model = "simple-tfidf"
    
    def embed(self, text: str) -> EmbeddingResult:
        embedding = self._compute_embedding(text)
        return EmbeddingResult(
            text=text,
            embedding=embedding,
            model=self.model
        )
    
    def _compute_embedding(self, text: str) -> List[float]:
        """Compute a simple hash-based embedding."""
        # Tokenize
        words = text.lower().split()
        
        # Create sparse vector using hashing trick
        vector = [0.0] * self.vocab_size
        
        for word in words:
            # Hash word to bucket
            hash_val = int(hashlib.md5(word.encode()).hexdigest(), 16)
            bucket = hash_val % self.vocab_size
            
            # Sign based on another hash
            sign = 1 if (hash_val // self.vocab_size) % 2 == 0 else -1
            vector[bucket] += sign
        
        # Normalize
        norm = sum(v * v for v in vector) ** 0.5
        if norm > 0:
            vector = [v / norm for v in vector]
        
        return vector


class SemanticMatcher:
    """Match code items to documentation using semantic similarity."""
    
    def __init__(self, provider: Optional[EmbeddingProvider] = None,
                 similarity_threshold: float = 0.7,
                 cache_dir: Optional[Path] = None):
        self.provider = provider or SimpleEmbeddings()
        self.similarity_threshold = similarity_threshold
        self.cache_dir = cache_dir
        self._cache: Dict[str, EmbeddingResult] = {}
        
        if cache_dir:
            self._load_cache()
    
    def _cache_key(self, text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()[:16]
    
    def _load_cache(self) -> None:
        if not self.cache_dir:
            return
        
        cache_file = self.cache_dir / "embeddings_cache.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                    for key, value in data.items():
                        self._cache[key] = EmbeddingResult(**value)
            except Exception:
                pass
    
    def _save_cache(self) -> None:
        if not self.cache_dir:
            return
        
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = self.cache_dir / "embeddings_cache.json"
        
        data = {
            key: {'text': er.text, 'embedding': er.embedding, 'model': er.model}
            for key, er in self._cache.items()
        }
        
        with open(cache_file, 'w') as f:
            json.dump(data, f)
    
    def get_embedding(self, text: str) -> EmbeddingResult:
        """Get embedding for text, using cache if available."""
        key = self._cache_key(text)
        
        if key not in self._cache:
            self._cache[key] = self.provider.embed(text)
        
        return self._cache[key]
    
    def find_best_match(self, query: str, 
                        candidates: List[str]) -> Optional[Tuple[str, float]]:
        """Find the best matching candidate for a query."""
        if not candidates:
            return None
        
        query_emb = self.get_embedding(query)
        
        best_match = None
        best_score = 0.0
        
        for candidate in candidates:
            candidate_emb = self.get_embedding(candidate)
            score = query_emb.similarity(candidate_emb)
            
            if score > best_score:
                best_score = score
                best_match = candidate
        
        if best_score >= self.similarity_threshold:
            return (best_match, best_score)
        
        return None
    
    def find_similar_items(self, code_descriptions: Dict[str, str],
                           doc_descriptions: Dict[str, str]) -> List[Dict[str, Any]]:
        """Find semantically similar items between code and docs."""
        matches = []
        
        for code_name, code_desc in code_descriptions.items():
            best_match = self.find_best_match(
                code_desc,
                list(doc_descriptions.values())
            )
            
            if best_match:
                doc_text, score = best_match
                # Find doc name by description
                doc_name = next(
                    name for name, desc in doc_descriptions.items()
                    if desc == doc_text
                )
                
                matches.append({
                    'code_name': code_name,
                    'doc_name': doc_name,
                    'similarity': score,
                    'potential_rename': code_name != doc_name,
                })
        
        return matches
    
    def detect_semantic_drift(self, code_docstring: str,
                               external_doc: str) -> Dict[str, Any]:
        """Detect if a docstring and external documentation have drifted."""
        code_emb = self.get_embedding(code_docstring)
        doc_emb = self.get_embedding(external_doc)
        
        similarity = code_emb.similarity(doc_emb)
        
        return {
            'similarity': similarity,
            'has_drift': similarity < self.similarity_threshold,
            'severity': self._classify_drift_severity(similarity),
        }
    
    def _classify_drift_severity(self, similarity: float) -> str:
        """Classify drift severity based on similarity score."""
        if similarity >= 0.9:
            return 'none'
        elif similarity >= 0.7:
            return 'info'
        elif similarity >= 0.5:
            return 'warning'
        else:
            return 'critical'
    
    def save(self) -> None:
        """Save embedding cache to disk."""
        self._save_cache()


def get_provider(provider_type: str = "simple", **kwargs) -> EmbeddingProvider:
    """Factory function to get embedding provider."""
    if provider_type == "openai":
        return OpenAIEmbeddings(**kwargs)
    elif provider_type == "local":
        return LocalEmbeddings(**kwargs)
    else:
        return SimpleEmbeddings(**kwargs)


if __name__ == '__main__':
    # Demo
    print("Embedding Demo")
    print("=" * 50)
    
    provider = SimpleEmbeddings()
    matcher = SemanticMatcher(provider, similarity_threshold=0.5)
    
    texts = [
        "Parse Python files using AST",
        "Parse JavaScript files using regex",
        "Compare code with documentation",
        "Generate drift report",
    ]
    
    query = "Analyze Python source code"
    best = matcher.find_best_match(query, texts)
    
    print(f"\nQuery: '{query}'")
    if best:
        print(f"Best match: '{best[0]}' (similarity: {best[1]:.3f})")
    else:
        print("No match found above threshold")
