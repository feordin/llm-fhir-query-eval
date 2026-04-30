# UI Design Plan — FHIR Query Evaluation Dashboard

## Page 1: Dashboard (Landing Page) — `/`

**Phenotype × Model Score Matrix**

- **Rows** = test cases grouped by phenotype
- **Columns** = dynamically generated from models that have results
- **Cells** = colored circles (green/red) + score. Dash `—` for not yet tested
- **Click a cell** → drill into that specific evaluation
- **Click a row** → see all evaluations for that phenotype
- **Summary bar** at bottom with aggregate stats (total test cases, evaluations, pass rate)

### Filters

| Filter | Values | Field |
|--------|--------|-------|
| **Mode** | Closed Book / Agentic (MCP) / All | `mcp_enabled` |
| **Complexity** | Simple / Medium / Hard | `metadata.complexity` |
| **Source** | PheKB / Manual / All | `source` |
| **Status** | Pass / Fail / Not Tested | `passed` |
| **Resource Type** | Condition / Observation / etc. | `expected_query.resource_type` |
| **Model** | Checkboxes per model | Show/hide columns |

---

## Page 2: Phenotype Detail — `/phenotypes/:id`

Shows all evaluations for one test case:

- **Prompt** displayed prominently (the natural language query)
- **Expected query** with code system details
- **Algorithm path** info from metadata
- **Results table**: Model, Mode (closed/agentic), Score, Exec F1, Semantic pass/fail, Status, Date
- Click any row to drill into full evaluation detail

---

## Page 3: Evaluation Detail — `/evaluations/:id`

Deep dive into one evaluation run:

- **Score breakdown**: Overall, Execution F1, Precision, Recall, Semantic match
- **Query comparison**: Expected vs Generated side-by-side with diff highlighting
- **Raw LLM response**: The full text returned by the model
- **Execution details**: Expected vs actual result counts, missing/extra resource IDs
- **Semantic differences**: Resource type match, parameter-level comparison

---

## Page 4: Run Evaluation — `/evaluate`

Form to kick off new evaluations (future work).

---

## Implementation Order

### Backend (required first)

1. **Results API endpoints**
   - `GET /api/results` — list all results with optional filters
   - `GET /api/results/:id` — get single result by evaluation_id
   - `GET /api/results?test_case_id=X` — filter by test case
   - `GET /api/results?model=X` — filter by model
   - `GET /api/results?mcp_enabled=true/false` — filter by mode

2. **Dashboard aggregation endpoint**
   - `GET /api/dashboard` — returns phenotype × model matrix with scores

### Frontend

1. TypeScript types mirroring backend Pydantic models
2. API client using Axios + React Query
3. Dashboard page with score matrix table + filters
4. Phenotype detail page with prompt display + result table
5. Evaluation detail page with score breakdown + query diff
6. Shared components: ScoreCell, FilterBar, QueryDisplay, DiffView

---

## Data Shape Examples

### Dashboard Matrix Response

```json
{
  "models": ["claude-3-5-sonnet", "gpt-4o", "command"],
  "test_cases": [
    {
      "id": "phekb-type-2-diabetes-dx",
      "name": "Type 2 Diabetes (Dx)",
      "source": "phekb",
      "complexity": "medium",
      "resource_type": "Condition",
      "results": {
        "claude-3-5-sonnet": { "score": 0.85, "passed": true, "mcp_enabled": false, "evaluation_id": "..." },
        "gpt-4o": { "score": 0.72, "passed": true, "mcp_enabled": false, "evaluation_id": "..." },
        "command": { "score": 0.0, "passed": false, "mcp_enabled": false, "evaluation_id": "..." }
      }
    }
  ],
  "summary": {
    "total_test_cases": 93,
    "total_evaluations": 7,
    "pass_rate": 0.42
  }
}
```
