import json
from typing import Optional

import requests


class FHIRClient:
    """Synchronous FHIR client for querying a fhir-candle test server."""

    def __init__(
        self,
        base_url: str = "http://localhost:8080",
        fhir_version: str = "fhir",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.fhir_version = fhir_version
        self.endpoint = f"{self.base_url}/{self.fhir_version}"
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Accept": "application/fhir+json",
                "Content-Type": "application/fhir+json",
            }
        )

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    def health_check(self) -> bool:
        """Return True if the FHIR server is reachable and returns 200 on /metadata."""
        try:
            response = self._session.get(f"{self.endpoint}/metadata", timeout=10)
            return response.status_code == 200
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Loading data
    # ------------------------------------------------------------------

    def load_bundle(self, bundle: dict) -> dict:
        """POST a FHIR transaction bundle to the server.

        Args:
            bundle: A Synthea-generated FHIR transaction bundle (type="transaction").

        Returns:
            The server's response parsed as a dict.

        Raises:
            requests.HTTPError: If the server returns a non-2xx status.
        """
        response = self._session.post(
            self.endpoint,
            data=json.dumps(bundle),
            timeout=60,
        )
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise requests.HTTPError(
                f"Failed to load bundle (HTTP {response.status_code}): {response.text}",
                response=response,
            ) from exc
        return response.json()

    def load_bundle_from_file(self, file_path: str) -> dict:
        """Read a FHIR transaction bundle JSON file and load it to the server.

        Args:
            file_path: Absolute or relative path to the bundle JSON file.

        Returns:
            The server's response parsed as a dict.
        """
        with open(file_path, "r", encoding="utf-8") as fh:
            bundle = json.load(fh)
        return self.load_bundle(bundle)

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------

    def execute_query(self, query_url: str) -> dict:
        """Execute a FHIR search query and return the raw Bundle response.

        Args:
            query_url: A relative FHIR query string such as
                       "Condition?code=http://loinc.org|2339-0".

        Returns:
            The parsed Bundle JSON as a dict.

        Raises:
            requests.HTTPError: If the server returns a non-2xx status.
        """
        url = f"{self.endpoint}/{query_url.lstrip('/')}"
        response = self._session.get(url, timeout=30)
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise requests.HTTPError(
                f"FHIR query failed (HTTP {response.status_code}) for '{query_url}': {response.text}",
                response=response,
            ) from exc
        return response.json()

    def get_resource_ids(self, query_url: str) -> list[str]:
        """Execute a query and return a sorted list of unique resource IDs.

        Each Bundle entry is expected to have a shape of
        ``{"resource": {"id": "..."}, ...}``.

        Returns:
            Sorted list of unique resource ID strings. Empty list when no
            entries are present.
        """
        bundle = self.execute_query(query_url)
        entries: list[dict] = bundle.get("entry", []) or []
        ids: set[str] = set()
        for entry in entries:
            resource = entry.get("resource", {})
            resource_id: Optional[str] = resource.get("id")
            if resource_id:
                ids.add(resource_id)
        return sorted(ids)

    def get_resource_count(self, query_url: str) -> int:
        """Execute a query and return the total number of matching resources.

        Uses ``bundle.total`` when present, falls back to the number of
        entries in the response, and returns 0 when neither is available.
        """
        bundle = self.execute_query(query_url)
        if "total" in bundle:
            return int(bundle["total"])
        entries = bundle.get("entry")
        if entries is not None:
            return len(entries)
        return 0

    def get_patient_ids_from_query(self, query_url: str) -> list[str]:
        """Execute a query and return sorted unique patient IDs referenced by the results.

        Extracts the patient UUID from ``resource.subject.reference`` fields
        that follow the ``"Patient/<uuid>"`` pattern.

        Returns:
            Sorted list of unique patient ID strings. Empty list when no
            subject references are found.
        """
        bundle = self.execute_query(query_url)
        entries: list[dict] = bundle.get("entry", []) or []
        patient_ids: set[str] = set()
        for entry in entries:
            resource = entry.get("resource", {})
            subject = resource.get("subject", {})
            reference: Optional[str] = subject.get("reference")
            if reference and reference.startswith("Patient/"):
                patient_id = reference.split("/", 1)[1]
                if patient_id:
                    patient_ids.add(patient_id)
        return sorted(patient_ids)
