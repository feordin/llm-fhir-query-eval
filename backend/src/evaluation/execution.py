import logging
import sys
from pathlib import Path

backend_path = Path(__file__).parent.parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from src.api.models.evaluation import ExecutionMatchResult

logger = logging.getLogger(__name__)


class ExecutionEvaluator:
    """Compares FHIR query results by executing both queries against the server."""

    def __init__(self, fhir_client):
        self.fhir_client = fhir_client

    def evaluate(self, expected_query_url: str, generated_query_url: str) -> ExecutionMatchResult:
        """Execute both queries and compare result sets.

        Uses resource IDs for comparison. Calculates precision, recall, F1.
        """
        # Get IDs from expected query
        try:
            expected_ids = set(self.fhir_client.get_resource_ids(expected_query_url))
        except Exception as e:
            logger.error(f"Failed to execute expected query '{expected_query_url}': {e}")
            expected_ids = set()

        # Get IDs from generated query
        try:
            generated_ids = set(self.fhir_client.get_resource_ids(generated_query_url))
        except Exception as e:
            logger.error(f"Failed to execute generated query '{generated_query_url}': {e}")
            generated_ids = set()

        # Calculate metrics
        intersection = expected_ids & generated_ids

        precision = len(intersection) / len(generated_ids) if generated_ids else 0.0
        recall = len(intersection) / len(expected_ids) if expected_ids else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

        return ExecutionMatchResult(
            passed=f1 >= 0.8,
            expected_count=len(expected_ids),
            actual_count=len(generated_ids),
            expected_ids=sorted(expected_ids),
            actual_ids=sorted(generated_ids),
            precision=round(precision, 4),
            recall=round(recall, 4),
            f1_score=round(f1, 4),
        )

    def evaluate_multi_query_patient_union(
        self, expected_patient_ids: list[str], generated_query_urls: list[str]
    ) -> ExecutionMatchResult:
        """Evaluate multiple generated queries against expected patient IDs.

        Runs each generated query, extracts patient IDs from the results,
        unions them, and compares against the expected patient ID set.
        This is the evaluation mode for multi-query test cases where the
        LLM generates multiple FHIR queries targeting different resource types.
        """
        expected_ids = set(expected_patient_ids)

        # Union patient IDs from all generated queries
        generated_ids = set()
        for url in generated_query_urls:
            try:
                patient_ids = set(self.fhir_client.get_patient_ids_from_query(url))
                generated_ids |= patient_ids
                logger.info(f"Query '{url[:80]}' returned {len(patient_ids)} patients")
            except Exception as e:
                logger.error(f"Failed to execute generated query '{url}': {e}")

        # Calculate metrics on patient-level union
        intersection = expected_ids & generated_ids

        precision = len(intersection) / len(generated_ids) if generated_ids else 0.0
        recall = len(intersection) / len(expected_ids) if expected_ids else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

        return ExecutionMatchResult(
            passed=f1 >= 0.8,
            expected_count=len(expected_ids),
            actual_count=len(generated_ids),
            expected_ids=sorted(expected_ids),
            actual_ids=sorted(generated_ids),
            precision=round(precision, 4),
            recall=round(recall, 4),
            f1_score=round(f1, 4),
        )
