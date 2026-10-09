"""Local semantic theme suggestions. No automatic personnel decisions."""
import math

MODEL_NAME = 'sentence-transformers/all-MiniLM-L6-v2'
MIN_SIMILARITY = 0.30
MIN_MARGIN = 0.05
REVIEW = 'Needs review'
THEMES = {
    'Communication': 'Customer updates are unclear or lack next steps, follow-up times, expectations, or explanations. Improve customer communication and clarity.',
    'Troubleshooting': 'Technical investigation lacks a structured diagnosis, reproducible steps, evidence, logs, hypotheses, or root cause analysis. Improve systematic troubleshooting.',
    'Documentation': 'Case notes, investigation records, resolution details, internal handover, or knowledge articles are incomplete or missing. Improve documentation and knowledge sharing.',
    'Product knowledge': 'The engineer needs to learn product features, configuration options, supported behavior, or how the product works. Improve product knowledge.',
}


def decide_theme(scores):
    if set(scores) != set(THEMES) or any(not math.isfinite(s) or not -1 <= s <= 1 for s in scores.values()):
        raise ValueError('Expected finite cosine scores for all four themes.')
    ranked = sorted(scores.items(), key=lambda pair: pair[1], reverse=True)
    theme, best = ranked[0]
    margin = best - ranked[1][1]
    if best < MIN_SIMILARITY:
        theme, reason = REVIEW, 'The note does not closely match the supported themes.'
    elif margin < MIN_MARGIN:
        theme, reason = REVIEW, 'The closest themes are too similar; more than one may apply.'
    else:
        reason = 'Closest matching theme; manager confirmation is required.'
    return {'theme': theme, 'reason': reason, 'scores': dict(ranked), 'best_score': best, 'margin': margin}


class SemanticNoteClassifier:
    def __init__(self):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(MODEL_NAME, device='cpu')
        self.names = list(THEMES)
        self.embeddings = self.model.encode_document(list(THEMES.values()))

    def analyze(self, note):
        if not note.strip():
            raise ValueError('Enter a case-review note first.')
        query = self.model.encode_query([note.strip()])
        scores = self.model.similarity(query, self.embeddings)[0].tolist()
        return decide_theme(dict(zip(self.names, scores)))
