"""Construction of the reproducible scikit-learn text-classification pipeline."""

from __future__ import annotations

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion, Pipeline


def build_text_pipeline(random_state: int = 42) -> Pipeline:
    """Build a word-and-character TF-IDF classifier.

    Word n-grams capture phrases such as "claim prize". Character n-grams help
    when messages contain spelling variants, abbreviations, or obfuscation.
    """

    features = FeatureUnion(
        transformer_list=[
            (
                "word_tfidf",
                TfidfVectorizer(
                    analyzer="word",
                    ngram_range=(1, 2),
                    min_df=1,
                    max_df=0.995,
                    max_features=50_000,
                    strip_accents="unicode",
                    sublinear_tf=True,
                ),
            ),
            (
                "character_tfidf",
                TfidfVectorizer(
                    analyzer="char_wb",
                    ngram_range=(3, 5),
                    min_df=1,
                    max_features=60_000,
                    sublinear_tf=True,
                ),
            ),
        ]
    )

    classifier = LogisticRegression(
        C=2.0,
        class_weight="balanced",
        max_iter=2_000,
        random_state=random_state,
        solver="lbfgs",
    )

    return Pipeline(
        steps=[
            ("features", features),
            ("classifier", classifier),
        ]
    )
