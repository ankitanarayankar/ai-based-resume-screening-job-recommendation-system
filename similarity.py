from sentence_transformers import SentenceTransformer, util

# Load model once (fast + good for projects)
model = SentenceTransformer('all-MiniLM-L6-v2')


def calculate_similarity(resume, job):
    """
    Semantic similarity using embeddings (much better than keyword matching)
    Returns score between 0 and 1
    """

    if not resume or not job:
        return 0.0

    embeddings = model.encode([resume, job])

    score = util.cos_sim(embeddings[0], embeddings[1])

    return float(score)