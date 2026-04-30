import uuid
import logging
import sys
from datetime import datetime
from pathlib import Path

backend_path = Path(__file__).parent.parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from src.api.models.evaluation import (
    EvaluationResult, EvaluationResults, GeneratedQuery,
    LLMJudgeResult, ParsedQuery,
)
from src.api.models.test_case import TestCase
from src.llm.provider import parse_fhir_queries_from_text
from .execution import ExecutionEvaluator
from .semantic import SemanticEvaluator
from .code_validation import CodeSystemValidator

logger = logging.getLogger(__name__)


class EvaluationRunner:
    """Orchestrates the full evaluation pipeline for a test case."""

    def __init__(self, fhir_client, llm_provider):
        self.fhir_client = fhir_client
        self.llm_provider = llm_provider
        self.execution_eval = ExecutionEvaluator(fhir_client)
        self.semantic_eval = SemanticEvaluator()
        self.code_eval = CodeSystemValidator()

    def run_single(self, test_case: TestCase, provider_name: str = "unknown", model_name: str = "unknown") -> EvaluationResult:
        """Run full evaluation for a single test case.

        Detects multi-query test cases automatically and uses the
        appropriate evaluation strategy.
        """
        is_multi = test_case.metadata.multi_query

        if is_multi:
            return self._run_multi_query(test_case, provider_name, model_name)
        else:
            return self._run_single_query(test_case, provider_name, model_name)

    def _run_single_query(self, test_case: TestCase, provider_name: str, model_name: str) -> EvaluationResult:
        """Original single-query evaluation path."""
        logger.info(f"Evaluating test case (single-query): {test_case.id}")

        # Step 1: Generate query from LLM
        logger.info(f"Sending prompt to LLM: {test_case.get_prompt()[:80]}...")
        generated = self.llm_provider.generate_fhir_query(test_case.get_prompt())
        logger.info(f"LLM generated query: {generated.parsed_query.url}")

        expected_url = test_case.expected_query.url
        generated_url = generated.parsed_query.url

        # Step 2: Execution evaluation
        logger.info("Running execution-based evaluation...")
        execution_result = self.execution_eval.evaluate(expected_url, generated_url)
        logger.info(f"Execution: P={execution_result.precision} R={execution_result.recall} F1={execution_result.f1_score}")

        # Step 3: Semantic evaluation
        logger.info("Running semantic evaluation...")
        semantic_result = self.semantic_eval.evaluate(expected_url, generated_url)
        logger.info(f"Semantic: passed={semantic_result.passed}, diffs={semantic_result.differences}")

        # Step 4: Code system validation
        code_validation_result = self.code_eval.evaluate(
            test_case.metadata.required_codes, [generated_url]
        )
        logger.info(
            f"Code validation: passed={code_validation_result.passed} "
            f"correct_systems={code_validation_result.correct_systems} "
            f"incorrect_systems={code_validation_result.incorrect_systems} "
            f"missing={len(code_validation_result.missing_codes)} "
            f"extra={len(code_validation_result.extra_codes)}"
        )

        # Step 5: Stub LLM judge
        llm_judge_result = LLMJudgeResult(
            passed=False, score=0.0, reasoning="LLM judge not yet implemented"
        )

        # Step 6: Overall score (50% execution F1 + 30% semantic + 20% code validation)
        semantic_score = 1.0 if semantic_result.passed else 0.0
        code_score = 1.0 if code_validation_result.passed else 0.0
        overall_score = round(
            execution_result.f1_score * 0.5
            + semantic_score * 0.3
            + code_score * 0.2,
            4,
        )

        return EvaluationResult(
            evaluation_id=str(uuid.uuid4()),
            test_case_id=test_case.id,
            timestamp=datetime.utcnow(),
            llm_provider=provider_name,
            model=model_name,
            mcp_enabled=False,
            generated_query=generated,
            evaluation_results=EvaluationResults(
                execution_match=execution_result,
                semantic_match=semantic_result,
                llm_judge=llm_judge_result,
                code_system_validation=code_validation_result,
            ),
            overall_score=overall_score,
            passed=overall_score >= 0.7,
        )

    def _run_multi_query(self, test_case: TestCase, provider_name: str, model_name: str) -> EvaluationResult:
        """Multi-query evaluation path.

        For test cases with metadata.multi_query=true:
        1. Send prompt to LLM (expects multiple FHIR queries in response)
        2. Parse all queries from the response
        3. Execute each query and collect patient IDs
        4. Compare the patient-level union against expected_patient_ids
        5. Score based on patient-level recall/precision
        """
        logger.info(f"Evaluating test case (multi-query): {test_case.id}")

        # Step 1: Generate queries from LLM
        logger.info(f"Sending prompt to LLM: {test_case.get_prompt()[:80]}...")
        generated = self.llm_provider.generate_fhir_query(test_case.get_prompt())
        raw_response = generated.raw_response

        # Step 2: Parse ALL queries from the response
        all_parsed = parse_fhir_queries_from_text(raw_response)

        if not all_parsed:
            # Fall back to the single parsed query
            all_parsed = [generated.parsed_query]

        # Build the GeneratedQuery with additional queries
        primary = all_parsed[0]
        additional = all_parsed[1:] if len(all_parsed) > 1 else []
        generated = GeneratedQuery(
            raw_response=raw_response,
            parsed_query=primary,
            additional_queries=additional,
        )

        query_urls = [q.url for q in all_parsed]
        logger.info(f"LLM generated {len(query_urls)} queries:")
        for url in query_urls:
            logger.info(f"  {url}")

        # Step 3: Patient-level execution evaluation
        expected_patient_ids = test_case.test_data.expected_patient_ids
        is_negation = test_case.metadata.negation
        if not expected_patient_ids:
            # Fall back to resource ID comparison with the primary query
            logger.warning("No expected_patient_ids set; falling back to single-query evaluation")
            expected_url = test_case.expected_query.url
            execution_result = self.execution_eval.evaluate(expected_url, primary.url)
        elif is_negation:
            logger.info(
                f"Running patient-level DIFFERENCE evaluation (negation) against "
                f"{len(expected_patient_ids)} expected patients..."
            )
            execution_result = self.execution_eval.evaluate_multi_query_patient_difference(
                expected_patient_ids, query_urls
            )
            logger.info(f"Execution: P={execution_result.precision} R={execution_result.recall} F1={execution_result.f1_score}")
        else:
            logger.info(f"Running patient-level union evaluation against {len(expected_patient_ids)} expected patients...")
            execution_result = self.execution_eval.evaluate_multi_query_patient_union(
                expected_patient_ids, query_urls
            )
            logger.info(f"Execution: P={execution_result.precision} R={execution_result.recall} F1={execution_result.f1_score}")

        # Step 4: Semantic evaluation — check how many expected queries the LLM covered
        expected_queries = test_case.metadata.expected_queries
        semantic_result = self._evaluate_multi_query_coverage(expected_queries, query_urls)
        logger.info(f"Query coverage: {semantic_result.differences}")

        # Step 5: Code system validation across all generated queries
        code_validation_result = self.code_eval.evaluate(
            test_case.metadata.required_codes, query_urls
        )
        logger.info(
            f"Code validation: passed={code_validation_result.passed} "
            f"correct_systems={code_validation_result.correct_systems} "
            f"incorrect_systems={code_validation_result.incorrect_systems} "
            f"missing={len(code_validation_result.missing_codes)} "
            f"extra={len(code_validation_result.extra_codes)}"
        )

        # Step 6: Stub LLM judge
        llm_judge_result = LLMJudgeResult(
            passed=False, score=0.0, reasoning="LLM judge not yet implemented"
        )

        # Step 7: Overall score (60% execution F1 + 20% query coverage + 20% code validation)
        coverage_score = 1.0 if semantic_result.passed else (
            0.5 if any("covered" in d.lower() for d in semantic_result.differences) else 0.0
        )
        code_score = 1.0 if code_validation_result.passed else 0.0
        overall_score = round(
            execution_result.f1_score * 0.6
            + coverage_score * 0.2
            + code_score * 0.2,
            4,
        )

        return EvaluationResult(
            evaluation_id=str(uuid.uuid4()),
            test_case_id=test_case.id,
            timestamp=datetime.utcnow(),
            llm_provider=provider_name,
            model=model_name,
            mcp_enabled=False,
            generated_query=generated,
            evaluation_results=EvaluationResults(
                execution_match=execution_result,
                semantic_match=semantic_result,
                llm_judge=llm_judge_result,
                code_system_validation=code_validation_result,
            ),
            overall_score=overall_score,
            passed=overall_score >= 0.7,
        )

    def _evaluate_multi_query_coverage(
        self, expected_queries: list[str], generated_urls: list[str]
    ) -> "SemanticMatchResult":
        """Check how many of the expected query types the LLM covered.

        For multi-query test cases, semantic evaluation checks whether the
        LLM generated queries covering each expected resource type, rather
        than exact parameter matching.
        """
        from src.api.models.evaluation import SemanticMatchResult

        if not expected_queries:
            return SemanticMatchResult(
                passed=True, resource_type_match=True,
                parameters_match=True, differences=[]
            )

        # Extract resource types from expected and generated
        expected_types = set()
        for q in expected_queries:
            rt = q.split('?')[0].split('/')[-1]
            expected_types.add(rt)

        generated_types = set()
        for url in generated_urls:
            rt = url.split('?')[0].split('/')[-1]
            generated_types.add(rt)

        covered = expected_types & generated_types
        missing = expected_types - generated_types
        extra = generated_types - expected_types

        differences = []
        if covered:
            differences.append(f"Covered resource types: {', '.join(sorted(covered))}")
        if missing:
            differences.append(f"Missing resource types: {', '.join(sorted(missing))}")
        if extra:
            differences.append(f"Extra resource types: {', '.join(sorted(extra))}")

        coverage_ratio = len(covered) / len(expected_types) if expected_types else 1.0
        differences.append(f"Query coverage: {len(covered)}/{len(expected_types)} expected query types")

        all_covered = len(missing) == 0
        resource_type_match = len(missing) == 0

        return SemanticMatchResult(
            passed=all_covered,
            resource_type_match=resource_type_match,
            parameters_match=all_covered,
            differences=differences,
        )
