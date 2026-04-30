import json
import os
from collections import defaultdict
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from src.api.models.evaluation import EvaluationResult
from src.api.routes.test_cases import list_test_case_ids, load_test_case
from src.utils.config import settings

router = APIRouter()


def load_all_results() -> List[EvaluationResult]:
    """Load all evaluation results from disk."""
    results = []
    if not os.path.exists(settings.results_dir):
        return results

    for filename in os.listdir(settings.results_dir):
        if not filename.endswith(".json"):
            continue
        filepath = os.path.join(settings.results_dir, filename)
        try:
            with open(filepath, "r") as f:
                data = json.load(f)
            results.append(EvaluationResult(**data))
        except Exception as e:
            print(f"Error loading result {filename}: {e}")

    return results


@router.get("", response_model=List[EvaluationResult])
async def list_results(
    test_case_id: Optional[str] = Query(None, description="Filter by test case ID"),
    model: Optional[str] = Query(None, description="Filter by model name"),
    mcp_enabled: Optional[bool] = Query(None, description="Filter by MCP enabled"),
    passed: Optional[bool] = Query(None, description="Filter by pass/fail"),
):
    """List evaluation results with optional filters."""
    results = load_all_results()

    if test_case_id is not None:
        results = [r for r in results if r.test_case_id == test_case_id]
    if model is not None:
        results = [r for r in results if r.model == model]
    if mcp_enabled is not None:
        results = [r for r in results if r.mcp_enabled == mcp_enabled]
    if passed is not None:
        results = [r for r in results if r.passed == passed]

    # Sort by timestamp descending
    results.sort(key=lambda r: r.timestamp, reverse=True)
    return results


def _provider_display_name(provider: str) -> str:
    """Map llm_provider values to display-friendly column names."""
    mapping = {
        "anthropic": "Claude",
        "claude": "Claude",
        "claude-cli": "Claude",
        "openai": "OpenAI",
        "gpt": "OpenAI",
        "google": "Gemini",
        "gemini": "Gemini",
        "command": "Local",
        "ollama": "Local",
        "local": "Local",
    }
    return mapping.get(provider.lower(), provider)


@router.get("/dashboard")
async def get_dashboard():
    """Get the phenotype x provider score matrix for the dashboard.

    Groups results by provider (Claude, OpenAI, Gemini, Local).
    For each phenotype x provider cell, shows the best score across
    all modes (closed book, agentic) and model variants.
    """
    results = load_all_results()

    # Group results by test_case_id → display_provider → best result
    results_by_case: Dict[str, Dict[str, EvaluationResult]] = defaultdict(dict)
    for result in results:
        provider = _provider_display_name(result.llm_provider)
        existing = results_by_case[result.test_case_id].get(provider)
        # Keep the best-scoring result per test_case × provider
        if existing is None or result.overall_score > existing.overall_score:
            results_by_case[result.test_case_id][provider] = result

    # Collect all unique providers (in display order)
    provider_order = ["Local", "Claude", "OpenAI", "Gemini"]
    all_providers = set()
    for case_results in results_by_case.values():
        all_providers.update(case_results.keys())
    # Sort by preferred order, then alphabetically for unknowns
    providers_list = [p for p in provider_order if p in all_providers]
    providers_list += sorted(all_providers - set(provider_order))

    # Build test case rows
    test_case_ids = list_test_case_ids()
    test_case_rows = []

    for tc_id in sorted(test_case_ids):
        try:
            tc = load_test_case(tc_id)
        except Exception:
            continue

        case_results = results_by_case.get(tc_id, {})
        provider_results = {}
        for provider_name, eval_result in case_results.items():
            provider_results[provider_name] = {
                "evaluation_id": eval_result.evaluation_id,
                "score": eval_result.overall_score,
                "passed": eval_result.passed,
                "mcp_enabled": eval_result.mcp_enabled,
                "model": eval_result.model,
                "timestamp": eval_result.timestamp.isoformat(),
                "f1_score": eval_result.evaluation_results.execution_match.f1_score,
                "semantic_passed": eval_result.evaluation_results.semantic_match.passed,
            }

        # Find best score across providers
        scores = [r["score"] for r in provider_results.values()]
        best_score = max(scores) if scores else None

        test_case_rows.append({
            "id": tc.id,
            "name": tc.name,
            "source": tc.source,
            "complexity": tc.metadata.complexity,
            "resource_type": tc.expected_query.resource_type,
            "multi_query": tc.metadata.multi_query,
            "tags": tc.metadata.tags,
            "algorithm_path": tc.metadata.algorithm_path,
            "results": provider_results,
            "best_score": best_score,
        })

    # Summary stats
    total_evaluations = len(results)
    passed_count = sum(1 for r in results if r.passed)
    pass_rate = passed_count / total_evaluations if total_evaluations > 0 else 0

    return {
        "models": providers_list,
        "test_cases": test_case_rows,
        "summary": {
            "total_test_cases": len(test_case_ids),
            "evaluated_test_cases": len(results_by_case),
            "total_evaluations": total_evaluations,
            "passed": passed_count,
            "failed": total_evaluations - passed_count,
            "pass_rate": round(pass_rate, 3),
        },
    }


@router.get("/{evaluation_id}", response_model=EvaluationResult)
async def get_result(evaluation_id: str):
    """Get a specific evaluation result."""
    filepath = os.path.join(settings.results_dir, f"{evaluation_id}.json")

    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail=f"Result {evaluation_id} not found")

    with open(filepath, "r") as f:
        data = json.load(f)

    return EvaluationResult(**data)
