import random
from typing import List, Dict, Any

class ControlledDataGenerator:
    """
    WBS 1.3: Controlled Data Generator
    Generates deterministic, semi-realistic datasets for the Test Harness.
    This ensures that the database is populated with meaningful data distributions 
    rather than purely random noise, which is critical for semantic Oracles.
    """
    
    def __init__(self, scenario: str = "general"):
        self.scenario = scenario
        # Simple vocabulary to generate semi-realistic texts
        self.vocab = {
            "ecommerce": ["laptop", "smartphone", "shoes", "jacket", "headphones", "monitor", "keyboard", "mouse"],
            "medical": ["xray", "mri", "blood test", "fever", "headache", "prescription", "diagnosis", "surgery"],
            "finance": ["loan", "credit", "mortgage", "stock", "bond", "interest rate", "portfolio", "dividend"],
            "general": ["apple", "banana", "car", "dog", "elephant", "fish", "guitar", "house", "island"]
        }
        
    def generate_corpus(self, size: int, noise_ratio: float = 0.2) -> List[Dict[str, Any]]:
        """
        Generate a corpus of texts with a specific distribution.
        - Primary domain items (1 - noise_ratio)
        - Out-of-domain noise (noise_ratio)
        """
        # WBS 3.4: Extract a simple domain keyword from scenario to avoid noise
        scenario_lower = self.scenario.lower()
        active_domain = "general"
        for domain in self.vocab.keys():
            if domain in scenario_lower:
                active_domain = domain
                break
        
        domain_words = self.vocab.get(active_domain, self.vocab["general"])
        noise_words = [word for domain, words in self.vocab.items() if domain != active_domain for word in words]
        
        corpus = []
        for i in range(size):
            is_noise = random.random() < noise_ratio
            if is_noise and noise_words:
                word = random.choice(noise_words)
                text = f"Standard {word} product for general use"
                category = "noise"
            else:
                word = random.choice(domain_words)
                text = f"High-quality {word} with premium features"
                category = "domain"
                
            corpus.append({
                "text": text,
                "metadata": {
                    "id": i,
                    "category": category,
                    "domain": active_domain
                }
            })
            
        return corpus
