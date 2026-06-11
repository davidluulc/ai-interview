from backend_python import knowledge_bases
from backend_python.rag_explain import RETRIEVER_LABELS
from backend_python.rag_store import VALID_KNOWLEDGE_BASES as STORE_VALID_KNOWLEDGE_BASES


def test_knowledge_base_constants_include_all_rags() -> None:
    assert knowledge_bases.ROLE_KNOWLEDGE == "role_knowledge"
    assert knowledge_bases.QUESTION_BANK == "question_bank"
    assert knowledge_bases.CANDIDATE_MEMORY == "candidate_memory"
    assert knowledge_bases.VALID_KNOWLEDGE_BASES == {
        "role_knowledge",
        "question_bank",
        "candidate_memory",
    }


def test_modules_share_central_knowledge_base_definitions() -> None:
    assert STORE_VALID_KNOWLEDGE_BASES == knowledge_bases.VALID_KNOWLEDGE_BASES
    assert set(RETRIEVER_LABELS) == knowledge_bases.VALID_KNOWLEDGE_BASES
