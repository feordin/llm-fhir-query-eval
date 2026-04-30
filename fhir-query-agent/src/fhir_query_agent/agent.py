"""Core agent loop for FHIR query generation.

The agent loop is model-agnostic: it works with any LLM adapter that
implements the LLMAdapter interface. The loop sends messages to the LLM,
dispatches tool calls, feeds results back, and repeats until the LLM
produces a final answer (no more tool calls).
"""

import json
import logging
import time
from dataclasses import dataclass, field

from fhir_query_agent.adapters.base import AdapterResponse, LLMAdapter, ToolCall
from fhir_query_agent.prompts import SYSTEM_PROMPT, INTERACTIVE_WELCOME
from fhir_query_agent.tools import FHIRQueryTools

logger = logging.getLogger(__name__)


@dataclass
class ToolCallRecord:
    """Record of a single tool call for the trace log."""

    iteration: int
    tool_name: str
    arguments: dict
    result: dict
    duration_ms: int = 0


@dataclass
class AgentResult:
    """Result from the agent's query generation process.

    Attributes:
        queries: Generated FHIR query URLs (relative paths).
        explanation: The agent's reasoning and final answer text.
        tool_trace: All tool calls made during generation (for transparency).
        iterations: Number of LLM round-trips taken.
        success: Whether the agent completed successfully.
        error: Error message if the agent failed.
    """

    queries: list[str] = field(default_factory=list)
    explanation: str = ""
    tool_trace: list[ToolCallRecord] = field(default_factory=list)
    iterations: int = 0
    success: bool = True
    error: str = ""


class FHIRQueryAgent:
    """Agent that generates accurate FHIR queries using tools.

    The agent follows a systematic workflow:
    1. Look up clinical codes via UMLS
    2. Check what code systems the FHIR server uses (sample resources)
    3. Crosswalk codes if needed
    4. Construct and test the query
    5. Return the final query with explanation

    Args:
        llm_adapter: An LLM adapter (OllamaAdapter, AnthropicAdapter, etc.).
        fhir_base_url: Base URL of the FHIR server.
        umls_api_key: Optional UMLS API key for terminology lookups.
        max_iterations: Maximum number of LLM round-trips (safety limit).
    """

    def __init__(
        self,
        llm_adapter: LLMAdapter,
        fhir_base_url: str,
        umls_api_key: str = None,
        max_iterations: int = 10,
    ):
        self.llm = llm_adapter
        self.tools = FHIRQueryTools(fhir_base_url, umls_api_key)
        self.max_iterations = max_iterations

    def generate_query(self, prompt: str) -> AgentResult:
        """Run the agent loop to generate a FHIR query from natural language.

        Args:
            prompt: Natural language clinical data request.

        Returns:
            AgentResult with generated queries, explanation, and tool trace.
        """
        result = AgentResult()

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        tool_defs = self.tools.get_tool_definitions()

        for iteration in range(1, self.max_iterations + 1):
            result.iterations = iteration
            logger.info(f"Iteration {iteration}/{self.max_iterations}")

            try:
                response = self.llm.chat(messages, tool_defs)
            except Exception as e:
                result.success = False
                result.error = f"LLM call failed: {str(e)}"
                logger.error(result.error)
                break

            # If the LLM produced a final response (no tool calls), we're done
            if response.is_final:
                result.explanation = response.content
                result.queries = self._extract_queries(response.content)
                break

            # Append the assistant's message (with tool calls) to history
            assistant_msg = self._build_assistant_message(response)
            messages.append(assistant_msg)

            # Execute each tool call and add results to messages
            for tc in response.tool_calls:
                start = time.time()
                tool_result = self.tools.execute(tc.name, tc.arguments)
                duration_ms = int((time.time() - start) * 1000)

                # Record in trace
                record = ToolCallRecord(
                    iteration=iteration,
                    tool_name=tc.name,
                    arguments=tc.arguments,
                    result=tool_result,
                    duration_ms=duration_ms,
                )
                result.tool_trace.append(record)
                logger.info(
                    f"  Tool: {tc.name}({tc.arguments}) -> "
                    f"{tool_result.get('status', '?')} ({duration_ms}ms)"
                )

                # Add tool result to messages
                messages.append({
                    "role": "tool",
                    "content": json.dumps(tool_result, default=str),
                })

            # If LLM also produced text content alongside tool calls, note it
            if response.content:
                # Some models return content alongside tool calls
                logger.debug(f"  LLM text: {response.content[:100]}...")
        else:
            # Hit max iterations
            result.success = False
            result.error = (
                f"Reached maximum iterations ({self.max_iterations}). "
                "The agent may need more steps or the query is too complex."
            )
            # Still try to extract any queries from the last response
            if messages and messages[-1].get("role") == "assistant":
                content = messages[-1].get("content", "")
                if content:
                    result.explanation = content
                    result.queries = self._extract_queries(content)

        return result

    def interactive(self):
        """Run in interactive chat mode.

        User types natural language prompts, and the agent generates
        FHIR queries with full tool trace output.
        """
        print(INTERACTIVE_WELCOME)
        print(f"FHIR Server: {self.tools.fhir_base_url}")
        print(f"UMLS:        {'configured' if self.tools.umls_api_key else 'not configured'}")
        print(f"LLM:         {getattr(self.llm, 'model', 'unknown')}")
        print()

        while True:
            try:
                prompt = input("Query> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nGoodbye!")
                break

            if not prompt:
                continue
            if prompt.lower() in ("quit", "exit", "q"):
                print("Goodbye!")
                break

            print()
            result = self.generate_query(prompt)

            # Display tool trace
            if result.tool_trace:
                print("--- Tool Calls ---")
                for tc in result.tool_trace:
                    status = tc.result.get("status", "?")
                    print(f"  [{tc.iteration}] {tc.name}({_compact_args(tc.arguments)}) -> {status} ({tc.duration_ms}ms)")
                print()

            # Display result
            if result.queries:
                print("--- FHIR Queries ---")
                for q in result.queries:
                    print(f"  {q}")
                print()

            if result.explanation:
                print("--- Explanation ---")
                print(result.explanation)
                print()

            if not result.success:
                print(f"--- Error ---\n  {result.error}\n")

            print(f"({result.iterations} iterations, {len(result.tool_trace)} tool calls)")
            print()

    def close(self):
        """Clean up resources."""
        self.tools.close()

    def _build_assistant_message(self, response: AdapterResponse) -> dict:
        """Build an assistant message for the conversation history.

        Handles the different formats expected by various LLM providers.
        """
        msg: dict = {"role": "assistant"}

        if response.content:
            msg["content"] = response.content
        else:
            msg["content"] = ""

        if response.tool_calls:
            msg["tool_calls"] = [
                {
                    "function": {
                        "name": tc.name,
                        "arguments": tc.arguments,
                    }
                }
                for tc in response.tool_calls
            ]

        return msg

    def _extract_queries(self, text: str) -> list[str]:
        """Extract FHIR query URLs from the agent's final response text.

        Looks for patterns like ResourceType?param=value in the text.
        """
        if not text:
            return []

        queries = []
        # Common FHIR resource types that start a query
        resource_prefixes = (
            "Patient", "Condition", "Observation", "MedicationRequest",
            "MedicationStatement", "Procedure", "Encounter", "Immunization",
            "AllergyIntolerance", "DiagnosticReport", "ServiceRequest",
            "CarePlan", "Goal", "DocumentReference", "Device",
            "DeviceUseStatement", "Specimen", "Coverage",
        )

        for line in text.split("\n"):
            line = line.strip().strip("`").strip()
            # Remove common markdown artifacts
            if line.startswith("- "):
                line = line[2:]
            if line.startswith("* "):
                line = line[2:]
            # Check if line looks like a FHIR query
            for prefix in resource_prefixes:
                if line.startswith(f"{prefix}?") or line.startswith(f"/{prefix}?"):
                    query = line.lstrip("/")
                    if query not in queries:
                        queries.append(query)
                    break

        return queries


def _compact_args(args: dict) -> str:
    """Format tool arguments compactly for display."""
    parts = []
    for k, v in args.items():
        val = str(v)
        if len(val) > 40:
            val = val[:37] + "..."
        parts.append(f"{k}={val}")
    return ", ".join(parts)
