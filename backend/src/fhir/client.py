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

    def get_patient_ids_from_query(
        self,
        query_url: str,
        resolve_stable_ids: bool = True,
        page_size: int = 200,
        max_pages: int = 50,
    ) -> list[str]:
        """Execute a query and return sorted unique patient IDs referenced by the results.

        Walks pagination via Bundle.link[rel="next"]. Use ``page_size`` to set
        ``_count`` on the initial request (defaults to 200 to reduce round trips).

        Extracts patient IDs from results in two ways:
        1. ``resource.subject.reference`` (Patient/<id>) on Conditions, Medications, etc.
        2. ``resource.id`` when the result IS a Patient resource (for Patient queries
           and `_revinclude` bundles).

        When ``resolve_stable_ids=True`` (default), each HAPI patient ID is mapped
        to its stable Synthea identifier via Patient.identifier. This is required for
        comparing results against fixtures whose ``expected_patient_ids`` were
        captured from the original Synthea bundles. Set to False to return raw
        HAPI internal IDs.

        Returns:
            Sorted list of unique patient ID strings. Empty list when no patient
            references are found.
        """
        # Inject _count if not present
        if "_count=" not in query_url:
            sep = "&" if "?" in query_url else "?"
            initial_url = f"{query_url}{sep}_count={page_size}"
        else:
            initial_url = query_url

        url: Optional[str] = initial_url
        hapi_patient_ids: set[str] = set()
        pages = 0
        while url and pages < max_pages:
            pages += 1
            # On the first page, url is a relative path; on subsequent pages,
            # the server returns absolute next-links.
            if url.startswith("http://") or url.startswith("https://"):
                response = self._session.get(url, timeout=30)
            else:
                response = self._session.get(
                    f"{self.endpoint}/{url.lstrip('/')}", timeout=30
                )
            response.raise_for_status()
            bundle = response.json()

            for entry in bundle.get("entry", []) or []:
                resource = entry.get("resource", {})
                rt = resource.get("resourceType")
                if rt == "Patient":
                    pid = resource.get("id")
                    if pid:
                        hapi_patient_ids.add(pid)
                    continue
                subject = resource.get("subject", {}) or resource.get("patient", {})
                reference: Optional[str] = (
                    subject.get("reference") if isinstance(subject, dict) else None
                )
                if reference and reference.startswith("Patient/"):
                    patient_id = reference.split("/", 1)[1]
                    if patient_id:
                        hapi_patient_ids.add(patient_id)

            next_url = None
            for link in bundle.get("link", []) or []:
                if link.get("relation") == "next":
                    next_url = link.get("url")
                    break
            url = next_url

        if not resolve_stable_ids:
            return sorted(hapi_patient_ids)

        stable_ids = self._resolve_stable_patient_ids(hapi_patient_ids)
        return sorted(stable_ids)

    _SYNTHEA_IDENTIFIER_SYSTEM = "https://github.com/synthetichealth/synthea"

    def _resolve_stable_patient_ids(self, hapi_ids: set[str]) -> set[str]:
        """Map HAPI internal patient IDs to stable Synthea UUIDs via Patient.identifier.

        Falls back to the HAPI ID when no Synthea identifier is found (e.g., on
        non-Synthea data sources). Caches lookups per client instance.
        """
        cache: dict[str, Optional[str]] = getattr(self, "_stable_id_cache", None)
        if cache is None:
            cache = {}
            self._stable_id_cache = cache

        resolved: set[str] = set()
        for hid in hapi_ids:
            if hid not in cache:
                cache[hid] = self._lookup_stable_id(hid)
            resolved.add(cache[hid] or hid)
        return resolved

    def _lookup_stable_id(self, hapi_id: str) -> Optional[str]:
        """Fetch Patient/<id> and extract the Synthea identifier value, if any."""
        try:
            response = self._session.get(f"{self.endpoint}/Patient/{hapi_id}", timeout=10)
            if response.status_code != 200:
                return None
            patient = response.json()
        except Exception:
            return None
        for ident in patient.get("identifier", []) or []:
            if ident.get("system") == self._SYNTHEA_IDENTIFIER_SYSTEM:
                value = ident.get("value")
                if value:
                    return value
        return None
