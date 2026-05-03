"""Generate document_analysis.json for state-B phekb-raw dirs.

State-B = has algorithm .doc/.docx/.pdf but no document_analysis.json yet.

For each target dir, reads the algorithm document(s), sends contents to Claude,
and writes a document_analysis.json matching the schema used elsewhere
(extracted_codes, clinical_criteria, algorithm_summary).

Usage:
    python scripts/extract_phekb_doc_analysis.py --dir <slug>           # one dir
    python scripts/extract_phekb_doc_analysis.py --all-state-b          # all six
    python scripts/extract_phekb_doc_analysis.py --dry-run --all-state-b  # preview only

Requires ANTHROPIC_API_KEY in env.
"""
from __future__ import annotations
import argparse
import datetime
import io
import json
import os
import re
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RAW = REPO / "data" / "phekb-raw"

# Load .env if present
env_path = REPO / ".env"
if env_path.exists() and "ANTHROPIC_API_KEY" not in os.environ:
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

EXTRACTION_PROMPT = """You are analyzing a PheKB (Phenotype KnowledgeBase) algorithm document. Extract the structured information below as a single JSON object — no prose, no markdown fence — matching this schema exactly:

{
  "phenotype_id": "<dir-slug>",
  "analyzed_files": [<list of source filenames you read>],
  "extracted_codes": [
    {
      "system": "ICD-10-CM" | "ICD-9-CM" | "SNOMED CT" | "RxNorm" | "LOINC" | "CPT" | "HCPCS",
      "code": "<the actual code as a string, e.g. '441.4', 'I71.4', '34803'>",
      "display": "<official display name>",
      "found_in": "<filename>",
      "context": "<short note on how this code is used in the algorithm — e.g. 'Case Type 2 inclusion', 'exclusion diagnosis', 'lab value LOINC'>"
    }
  ],
  "clinical_criteria": [
    "<plain-language criterion or threshold from the algorithm — e.g. 'Age 40-89 years', 'AKIN Stage 1: 1.5- to 2-fold increase in serum creatinine'>"
  ],
  "algorithm_summary": "<2-4 sentence narrative summary describing case definition, exclusions, and any temporal/threshold logic>",
  "analysis_timestamp": "<ISO-8601 UTC timestamp you'll fill in>"
}

Rules:
- Only emit codes that are explicitly present in the document (no inferences). Include every code you can find — diagnosis, procedure, medication, lab, exclusion.
- For wildcards or families like "493.x" or "I71" preserve as written but use a representative code (e.g. "493.90" not "493.x").
- If the document lists CUIs (e.g. C0021368), record them with system="SNOMED CT" only if they're SNOMED concepts; otherwise note in context.
- clinical_criteria should be free-form quoted phrases — age guards, lab thresholds, encounter requirements, exclusion logic.
- Output ONLY the JSON object. No commentary."""


def read_doc(path: Path) -> str:
    """Extract printable text from .doc, .docx, or .pdf. Best-effort."""
    suffix = path.suffix.lower()
    if suffix == ".docx":
        try:
            with zipfile.ZipFile(path) as z:
                xml = z.read("word/document.xml").decode("utf-8", errors="ignore")
            text = re.sub(r"<[^>]+>", " ", xml)
            text = re.sub(r"\s+", " ", text)
            return text
        except Exception as e:
            return f"<error reading {path.name}: {e}>"
    if suffix == ".doc":
        try:
            import olefile  # type: ignore
        except ImportError:
            return f"<install olefile to read {path.name}>"
        try:
            ole = olefile.OleFileIO(str(path))
            stream = ole.openstream("WordDocument").read()
            ole.close()
            chunks = re.findall(rb"[\x20-\x7e\r\n\t]{20,}", stream)
            return "\n".join(c.decode("ascii", errors="ignore") for c in chunks)
        except Exception as e:
            return f"<error reading {path.name}: {e}>"
    if suffix == ".pdf":
        try:
            import pypdf  # type: ignore
            r = pypdf.PdfReader(str(path))
            return "\n".join(p.extract_text() or "" for p in r.pages)
        except ImportError:
            return f"<install pypdf to read {path.name}>"
        except Exception as e:
            return f"<error reading {path.name}: {e}>"
    return f"<unsupported file type: {path.name}>"


def find_state_b_dirs() -> list[Path]:
    out = []
    for d in sorted(p for p in RAW.iterdir() if p.is_dir()):
        if (d / "document_analysis.json").exists():
            continue
        if any(f.suffix.lower() in (".doc", ".docx", ".pdf") for f in d.iterdir()):
            out.append(d)
    return out


def analyze_with_claude(slug: str, files: dict[str, str]) -> dict:
    import anthropic  # type: ignore
    client = anthropic.Anthropic()
    file_block = "\n\n".join(
        f"=== FILE: {name} ===\n{text[:50000]}" for name, text in files.items()
    )
    user_msg = (
        f"Phenotype slug: {slug}\n\n"
        f"Source documents:\n\n{file_block}\n\n"
        "Now produce the JSON object per the schema."
    )
    text_chunks: list[str] = []
    with client.messages.stream(
        model="claude-sonnet-4-5-20250929",
        max_tokens=32000,
        system=EXTRACTION_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
    ) as stream:
        for delta in stream.text_stream:
            text_chunks.append(delta)
    text = "".join(text_chunks).strip()
    # Strip optional code fence
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.DOTALL)
    return json.loads(text)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dir", help="Phenotype dir slug under data/phekb-raw/")
    p.add_argument("--all-state-b", action="store_true", help="Process all state-B dirs")
    p.add_argument("--dry-run", action="store_true", help="Read files and print summary, skip API call")
    p.add_argument("--force", action="store_true", help="Overwrite existing document_analysis.json")
    args = p.parse_args()

    if args.all_state_b:
        targets = find_state_b_dirs()
    elif args.dir:
        targets = [RAW / args.dir]
    else:
        sys.exit("Specify --dir <slug> or --all-state-b")

    for d in targets:
        if not d.is_dir():
            print(f"SKIP: {d} not a dir")
            continue
        out_path = d / "document_analysis.json"
        if out_path.exists() and not args.force:
            print(f"SKIP: {d.name} already has document_analysis.json (use --force)")
            continue
        docs = [f for f in d.iterdir() if f.suffix.lower() in (".doc", ".docx", ".pdf")]
        if not docs:
            print(f"SKIP: {d.name} has no algorithm doc")
            continue
        print(f"\n=== {d.name} ===")
        print(f"  files: {[f.name for f in docs]}")
        files = {f.name: read_doc(f) for f in docs}
        for n, t in files.items():
            print(f"  {n}: {len(t)} chars extracted (sample: {t[:80]!r})")
        if args.dry_run:
            continue
        try:
            analysis = analyze_with_claude(d.name, files)
        except Exception as e:
            print(f"  ERROR calling Claude: {e}")
            continue
        analysis["phenotype_id"] = d.name
        analysis["analyzed_files"] = [f.name for f in docs]
        analysis["analysis_timestamp"] = datetime.datetime.utcnow().isoformat() + "Z"
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(analysis, f, indent=2)
        codes_n = len(analysis.get("extracted_codes", []))
        criteria_n = len(analysis.get("clinical_criteria", []))
        print(f"  WROTE: {codes_n} codes, {criteria_n} criteria, "
              f"{len(analysis.get('algorithm_summary',''))} char summary")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
