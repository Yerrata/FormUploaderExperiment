from __future__ import annotations

import hashlib
import json
import os
import secrets
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from formc_app.models import (
    CandidateFormC,
    CaseMetadata,
    CaseState,
    CaseStatus,
    CaseSummary,
    EvidenceManifest,
    FilingRequest,
    MockSubmission,
    utc_now,
)


class CaseNotFoundError(LookupError):
    pass


class InvalidGuestTokenError(PermissionError):
    pass


class CaseStore:
    """Atomic, low-volume JSON storage for a single Yeratta property."""

    def __init__(self, root: Path):
        self.root = root
        self.cases_root = root / "cases"
        self.mock_submissions_root = root / "mock_submissions"
        self.cases_root.mkdir(parents=True, exist_ok=True)
        self.mock_submissions_root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _json_bytes(model: Any) -> bytes:
        if hasattr(model, "model_dump"):
            value = model.model_dump(mode="json")
        else:
            value = model
        return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")

    @staticmethod
    def _atomic_write(path: Path, content: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
        )
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_name, path)
        except BaseException:
            try:
                os.unlink(temporary_name)
            except FileNotFoundError:
                pass
            raise

    def _case_dir(self, case_id: str) -> Path:
        case_dir = self.cases_root / case_id
        if not case_dir.is_dir():
            raise CaseNotFoundError(case_id)
        return case_dir

    def create_case(
        self,
        *,
        check_in_date: date,
        check_out_date: date | None,
        room: str,
        form_b_reference: str,
        dummy_profile: str,
        token_lifetime: timedelta = timedelta(minutes=30),
    ) -> CaseMetadata:
        while True:
            suffix = secrets.token_hex(2).upper()
            case_id = f"YRT-{check_in_date:%Y%m%d}-{suffix}"
            case_dir = self.cases_root / case_id
            try:
                case_dir.mkdir(parents=True)
                break
            except FileExistsError:
                continue

        metadata = CaseMetadata(
            case_id=case_id,
            guest_token=secrets.token_urlsafe(24),
            guest_token_expires_at=utc_now() + token_lifetime,
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            room=room.strip(),
            form_b_reference=form_b_reference.strip(),
            dummy_profile=dummy_profile,
        )
        state = CaseState(case_id=case_id)
        (case_dir / "documents").mkdir()
        (case_dir / "evidence").mkdir()
        self._atomic_write(case_dir / "metadata.json", self._json_bytes(metadata))
        self._atomic_write(case_dir / "status.json", self._json_bytes(state))
        return metadata

    def load_metadata(self, case_id: str) -> CaseMetadata:
        path = self._case_dir(case_id) / "metadata.json"
        return CaseMetadata.model_validate_json(path.read_text("utf-8"))

    def save_metadata(self, metadata: CaseMetadata) -> None:
        path = self._case_dir(metadata.case_id) / "metadata.json"
        self._atomic_write(path, self._json_bytes(metadata))

    def load_state(self, case_id: str) -> CaseState:
        path = self._case_dir(case_id) / "status.json"
        return CaseState.model_validate_json(path.read_text("utf-8"))

    def update_status(
        self,
        case_id: str,
        status: CaseStatus,
        message: str,
        *,
        increment_attempt: bool = False,
    ) -> CaseState:
        state = self.load_state(case_id)
        state.status = status
        state.status_message = message
        state.status_changed_at = utc_now()
        if increment_attempt:
            state.attempt += 1
        self._atomic_write(
            self._case_dir(case_id) / "status.json",
            self._json_bytes(state),
        )
        return state

    def save_document(
        self,
        case_id: str,
        document_kind: str,
        original_filename: str | None,
        content: bytes,
    ) -> str:
        if document_kind not in {"passport", "visa", "guest_photo"}:
            raise ValueError("Unsupported document kind")
        suffix = Path(original_filename or "capture.jpg").suffix.lower()
        if suffix not in {".jpg", ".jpeg", ".png", ".webp", ".pdf"}:
            suffix = ".bin"
        relative_path = f"documents/{document_kind}{suffix}"
        self._atomic_write(self._case_dir(case_id) / relative_path, content)
        metadata = self.load_metadata(case_id)
        if document_kind == "passport":
            metadata.passport_document = relative_path
        elif document_kind == "visa":
            metadata.visa_document = relative_path
        else:
            metadata.guest_photo_document = relative_path
        self.save_metadata(metadata)
        return relative_path

    def document_path(self, case_id: str, relative_path: str) -> Path:
        case_dir = self._case_dir(case_id).resolve()
        path = (case_dir / relative_path).resolve()
        if case_dir not in path.parents or not path.is_file():
            raise ValueError("Case document path is missing or escapes its case folder")
        return path

    def document_sha256(self, case_id: str, relative_path: str) -> str:
        return self.sha256(self.document_path(case_id, relative_path).read_bytes())

    def save_candidate(self, candidate: CandidateFormC) -> None:
        path = self._case_dir(candidate.case_id) / "candidate.json"
        self._atomic_write(path, self._json_bytes(candidate))

    def candidate_sha256(self, candidate: CandidateFormC) -> str:
        return self.sha256(self._json_bytes(candidate))

    def canonical_candidate_bytes(self, candidate: CandidateFormC) -> bytes:
        return self._json_bytes(candidate)

    def save_filing_request(self, filing_request: FilingRequest) -> None:
        path = self._case_dir(filing_request.case_id) / "filing-request.json"
        if path.exists():
            existing = FilingRequest.model_validate_json(path.read_text("utf-8"))
            if (
                existing.candidate_sha256 != filing_request.candidate_sha256
                or existing.guest_photo_sha256 != filing_request.guest_photo_sha256
                or existing.guest_photo_source != filing_request.guest_photo_source
                or existing.guest_photo_suitability_confirmed_at
                != filing_request.guest_photo_suitability_confirmed_at
            ):
                raise ValueError("A different Filing Request already exists for this case")
            return
        self._atomic_write(path, self._json_bytes(filing_request))

    def load_filing_request(self, case_id: str) -> FilingRequest | None:
        path = self._case_dir(case_id) / "filing-request.json"
        if not path.exists():
            return None
        return FilingRequest.model_validate_json(path.read_text("utf-8"))

    def save_fill_plan(self, case_id: str, fill_plan: Any) -> None:
        path = self._case_dir(case_id) / "fill-plan.json"
        self._atomic_write(path, self._json_bytes(fill_plan))

    def load_candidate(self, case_id: str) -> CandidateFormC | None:
        path = self._case_dir(case_id) / "candidate.json"
        if not path.exists():
            return None
        return CandidateFormC.model_validate_json(path.read_text("utf-8"))

    def save_evidence(self, evidence: EvidenceManifest) -> None:
        path = self._case_dir(evidence.case_id) / "evidence" / "manifest.json"
        self._atomic_write(path, self._json_bytes(evidence))

    def load_evidence(self, case_id: str) -> EvidenceManifest | None:
        path = self._case_dir(case_id) / "evidence" / "manifest.json"
        if not path.exists():
            return None
        return EvidenceManifest.model_validate_json(path.read_text("utf-8"))

    def save_evidence_file(self, case_id: str, filename: str, content: bytes) -> str:
        safe_name = Path(filename).name
        relative_path = f"evidence/{safe_name}"
        self._atomic_write(self._case_dir(case_id) / relative_path, content)
        return relative_path

    def get_summary(self, case_id: str) -> CaseSummary:
        return CaseSummary(
            metadata=self.load_metadata(case_id),
            state=self.load_state(case_id),
            candidate=self.load_candidate(case_id),
            evidence=self.load_evidence(case_id),
        )

    def list_cases(self) -> list[CaseSummary]:
        summaries: list[CaseSummary] = []
        for case_dir in self.cases_root.iterdir():
            if not case_dir.is_dir():
                continue
            try:
                summaries.append(self.get_summary(case_dir.name))
            except (OSError, ValueError, CaseNotFoundError):
                continue
        return sorted(
            summaries,
            key=lambda item: (
                item.metadata.check_in_date,
                item.metadata.created_at,
            ),
        )

    def require_guest_token(self, token: str, *, editable: bool = True) -> CaseSummary:
        now = datetime.now(timezone.utc)
        for summary in self.list_cases():
            metadata = summary.metadata
            if not secrets.compare_digest(metadata.guest_token, token):
                continue
            if metadata.guest_token_expires_at < now:
                raise InvalidGuestTokenError("Guest Session has expired")
            if editable and summary.state.status in {
                CaseStatus.READY_FOR_FILING,
                CaseStatus.FILING,
                CaseStatus.PRE_SUBMIT_EVIDENCE_SEALED,
                CaseStatus.VERIFIED,
                CaseStatus.SUBMITTED_UNVERIFIED,
            }:
                raise InvalidGuestTokenError("Guest Session is no longer editable")
            return summary
        raise InvalidGuestTokenError("Guest Session link is invalid")

    def claim_ready_case(self, case_id: str) -> CaseState:
        case_dir = self._case_dir(case_id)
        state = self.load_state(case_id)
        if state.status != CaseStatus.READY_FOR_FILING:
            raise ValueError(f"Case is not ready: {state.status}")
        try:
            (case_dir / "worker.lock").mkdir()
        except FileExistsError as exc:
            raise ValueError("Case is already claimed") from exc
        try:
            return self.update_status(
                case_id,
                CaseStatus.FILING,
                "Filing Worker claimed the case",
                increment_attempt=True,
            )
        except BaseException:
            (case_dir / "worker.lock").rmdir()
            raise

    def release_claim(self, case_id: str) -> None:
        try:
            (self._case_dir(case_id) / "worker.lock").rmdir()
        except FileNotFoundError:
            pass

    def ready_case_ids(self) -> list[str]:
        return [
            summary.metadata.case_id
            for summary in self.list_cases()
            if summary.state.status == CaseStatus.READY_FOR_FILING
        ]

    def save_mock_submission(self, submission: MockSubmission) -> None:
        path = self.mock_submissions_root / f"{submission.case_id}.json"
        if path.exists():
            existing = MockSubmission.model_validate_json(path.read_text("utf-8"))
            if existing.fields != submission.fields:
                raise ValueError("Mock portal refuses a conflicting duplicate submission")
            return
        self._atomic_write(path, self._json_bytes(submission))

    def load_mock_submission(self, case_id: str) -> MockSubmission | None:
        path = self.mock_submissions_root / f"{case_id}.json"
        if not path.exists():
            return None
        return MockSubmission.model_validate_json(path.read_text("utf-8"))

    @staticmethod
    def sha256(content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()
