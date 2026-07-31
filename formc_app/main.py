from __future__ import annotations

import os
import re
import secrets
from datetime import date
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from formc_app.domain import (
    EXTRACTED_FIELD_NAMES,
    FIELD_BY_NAME,
    FORM_FIELDS,
    QUESTION_FIELD_NAMES,
    REQUIRED_FIELD_NAMES,
)
from formc_app.dummy_extraction import DUMMY_PROFILES, extract_dummy
from formc_app.models import (
    CandidateField,
    CandidateFormC,
    CaseStatus,
    FilingRequest,
    MockSubmission,
    utc_now,
)
from formc_app.storage import CaseNotFoundError, CaseStore, InvalidGuestTokenError


PACKAGE_ROOT = Path(__file__).parent
templates = Jinja2Templates(directory=PACKAGE_ROOT / "templates")


def _store(request: Request) -> CaseStore:
    return request.app.state.store


def _guest_case(request: Request, token: str, *, editable: bool = True):
    try:
        return _store(request).require_guest_token(token, editable=editable)
    except InvalidGuestTokenError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


def _candidate_display(candidate: CandidateFormC | None):
    if candidate is None:
        return []
    return [
        (field, candidate.fields.get(field.name))
        for field in FORM_FIELDS
        if field.name in candidate.fields
    ]


def _validate_candidate_input(field_name: str, value: str) -> None:
    definition = FIELD_BY_NAME[field_name]
    allowed_values = {choice_value for choice_value, _ in definition.choices}
    if allowed_values and value not in allowed_values:
        raise ValueError(f"Choose a supported value for {definition.label}")
    if definition.input_type == "date":
        try:
            date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(f"Enter a valid date for {definition.label}") from exc
    if definition.input_type == "time" and not re.fullmatch(
        r"(?:[01]\d|2[0-3]):[0-5]\d", value
    ):
        raise ValueError(f"Enter a valid 24-hour time for {definition.label}")


def create_app(data_root: Path | None = None) -> FastAPI:
    root = data_root or Path(os.environ.get("FORMC_DATA_DIR", "data"))
    app = FastAPI(title="Yeratta Form C", version="0.1.0")
    app.state.store = CaseStore(root)
    app.mount("/static", StaticFiles(directory=PACKAGE_ROOT / "static"), name="static")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/", response_class=HTMLResponse)
    async def home(request: Request):
        return RedirectResponse(request.url_for("staff_dashboard"), status_code=303)

    @app.get("/staff", response_class=HTMLResponse, name="staff_dashboard")
    async def staff_dashboard(request: Request, check_in_date: date | None = None):
        cases = _store(request).list_cases()
        available_dates = sorted(
            {summary.metadata.check_in_date for summary in cases},
            reverse=True,
        )
        selected_date = check_in_date or (available_dates[0] if available_dates else date.today())
        visible_cases = [
            summary
            for summary in cases
            if summary.metadata.check_in_date == selected_date
        ]
        return templates.TemplateResponse(
            request,
            "staff_dashboard.html",
            {
                "cases": visible_cases,
                "available_dates": available_dates,
                "selected_date": selected_date,
                "profiles": DUMMY_PROFILES,
                "status": CaseStatus,
            },
        )

    @app.post("/staff/cases", name="create_staff_case")
    async def create_staff_case(
        request: Request,
        check_in_date: date = Form(...),
        check_out_date: date | None = Form(None),
        room: str = Form(...),
        form_b_reference: str = Form(...),
        dummy_profile: str = Form(...),
    ):
        if dummy_profile not in DUMMY_PROFILES:
            raise HTTPException(status_code=400, detail="Unknown dummy profile")
        metadata = _store(request).create_case(
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            room=room,
            form_b_reference=form_b_reference,
            dummy_profile=dummy_profile,
        )
        return RedirectResponse(
            request.url_for("case_handoff", case_id=metadata.case_id),
            status_code=303,
        )

    @app.get("/staff/cases/{case_id}/handoff", response_class=HTMLResponse, name="case_handoff")
    async def case_handoff(request: Request, case_id: str):
        try:
            summary = _store(request).get_summary(case_id)
        except CaseNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Case not found") from exc
        guest_url = request.url_for("guest_capture", token=summary.metadata.guest_token)
        return templates.TemplateResponse(
            request,
            "case_handoff.html",
            {"case": summary, "guest_url": guest_url},
        )

    @app.get("/staff/cases/{case_id}", response_class=HTMLResponse, name="case_detail")
    async def case_detail(request: Request, case_id: str):
        try:
            summary = _store(request).get_summary(case_id)
        except CaseNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Case not found") from exc
        return templates.TemplateResponse(
            request,
            "case_detail.html",
            {
                "case": summary,
                "fields": _candidate_display(summary.candidate),
                "status": CaseStatus,
            },
        )

    @app.post("/staff/cases/{case_id}/run", name="run_case")
    async def run_case(request: Request, case_id: str, background_tasks: BackgroundTasks):
        try:
            summary = _store(request).get_summary(case_id)
        except CaseNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Case not found") from exc
        if summary.state.status != CaseStatus.READY_FOR_FILING:
            raise HTTPException(status_code=409, detail="Case is not ready for filing")
        from formc_app.worker import FilingWorker

        worker = FilingWorker(
            store=_store(request),
            base_url=str(request.base_url).rstrip("/"),
            headless=True,
        )
        background_tasks.add_task(worker.process_case, case_id)
        return RedirectResponse(request.url_for("case_detail", case_id=case_id), status_code=303)

    @app.post("/staff/cases/{case_id}/retry", name="retry_case")
    async def retry_case(request: Request, case_id: str):
        store = _store(request)
        try:
            summary = store.get_summary(case_id)
        except CaseNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Case not found") from exc
        if summary.state.status != CaseStatus.BLOCKED:
            raise HTTPException(status_code=409, detail="Only a safely blocked case can be retried")
        if store.load_mock_submission(case_id) is not None:
            raise HTTPException(
                status_code=409,
                detail="A submitted case must be reconciled, never retried",
            )
        store.update_status(
            case_id,
            CaseStatus.READY_FOR_FILING,
            "Safe pre-submit failure cleared; ready for another worker attempt",
        )
        return RedirectResponse(request.url_for("case_detail", case_id=case_id), status_code=303)

    @app.get("/staff/cases/{case_id}/evidence/{filename}", name="evidence_file")
    async def evidence_file(request: Request, case_id: str, filename: str):
        safe_name = Path(filename).name
        path = _store(request).cases_root / case_id / "evidence" / safe_name
        if not path.is_file():
            raise HTTPException(status_code=404, detail="Evidence not found")
        return FileResponse(path)

    @app.get("/guest/{token}/capture", response_class=HTMLResponse, name="guest_capture")
    async def guest_capture(request: Request, token: str):
        summary = _guest_case(request, token)
        if summary.candidate is not None:
            return RedirectResponse(request.url_for("guest_review", token=token), status_code=303)
        return templates.TemplateResponse(request, "guest_capture.html", {"case": summary})

    @app.post("/guest/{token}/capture")
    async def guest_capture_submit(
        request: Request,
        token: str,
        passport: UploadFile,
        visa: UploadFile,
    ):
        summary = _guest_case(request, token)
        passport_content = await passport.read()
        visa_content = await visa.read()
        if not passport_content or not visa_content:
            raise HTTPException(status_code=400, detail="Both photographs are required")
        if len(passport_content) > 15_000_000 or len(visa_content) > 15_000_000:
            raise HTTPException(status_code=413, detail="Each photograph must be under 15 MB")
        store = _store(request)
        store.save_document(summary.metadata.case_id, "passport", passport.filename, passport_content)
        store.save_document(summary.metadata.case_id, "visa", visa.filename, visa_content)
        fields = extract_dummy(summary.metadata.dummy_profile)
        staff_values = {
            "check_in_date": summary.metadata.check_in_date.isoformat(),
            "check_out_date": summary.metadata.check_out_date.isoformat()
            if summary.metadata.check_out_date
            else None,
            "room": summary.metadata.room,
            "form_b_reference": summary.metadata.form_b_reference,
        }
        for name, value in staff_values.items():
            fields[name] = CandidateField(value=value, source="staff")
        candidate = CandidateFormC(case_id=summary.metadata.case_id, fields=fields)
        store.save_candidate(candidate)
        store.update_status(
            summary.metadata.case_id,
            CaseStatus.GUEST_REVIEW,
            "Dummy extraction ready for guest review",
        )
        return RedirectResponse(request.url_for("guest_review", token=token), status_code=303)

    @app.get("/guest/{token}/review", response_class=HTMLResponse, name="guest_review")
    async def guest_review(request: Request, token: str):
        summary = _guest_case(request, token)
        if summary.candidate is None:
            return RedirectResponse(request.url_for("guest_capture", token=token), status_code=303)
        return templates.TemplateResponse(
            request,
            "guest_review.html",
            {
                "case": summary,
                "fields": [
                    (FIELD_BY_NAME[name], summary.candidate.fields[name])
                    for name in EXTRACTED_FIELD_NAMES
                ],
            },
        )

    @app.post("/guest/{token}/review")
    async def guest_review_submit(request: Request, token: str):
        summary = _guest_case(request, token)
        candidate = summary.candidate
        if candidate is None:
            raise HTTPException(status_code=409, detail="No extracted candidate exists")
        form = await request.form()
        for name in EXTRACTED_FIELD_NAMES:
            new_value = str(form.get(name, "")).strip()
            if not new_value:
                raise HTTPException(status_code=422, detail=f"{FIELD_BY_NAME[name].label} is required")
            try:
                _validate_candidate_input(name, new_value)
            except ValueError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
            current = candidate.fields[name]
            if new_value != current.value:
                candidate.fields[name] = CandidateField(
                    value=new_value,
                    source="guest_correction",
                    original_value=current.original_value or current.value,
                    corrected_at=utc_now(),
                )
        _store(request).save_candidate(candidate)
        _store(request).update_status(
            candidate.case_id,
            CaseStatus.NEEDS_ANSWERS,
            "Identity particulars reviewed; collecting missing mandatory answers",
        )
        return RedirectResponse(request.url_for("guest_question", token=token), status_code=303)

    @app.get("/guest/{token}/question", response_class=HTMLResponse, name="guest_question")
    async def guest_question(request: Request, token: str):
        summary = _guest_case(request, token)
        candidate = summary.candidate
        if candidate is None:
            return RedirectResponse(request.url_for("guest_capture", token=token), status_code=303)
        missing_questions = [name for name in QUESTION_FIELD_NAMES if not candidate.value(name)]
        if not missing_questions:
            return RedirectResponse(request.url_for("guest_confirm", token=token), status_code=303)
        field = FIELD_BY_NAME[missing_questions[0]]
        return templates.TemplateResponse(
            request,
            "guest_question.html",
            {"case": summary, "field": field},
        )

    @app.post("/guest/{token}/question")
    async def guest_question_submit(
        request: Request,
        token: str,
        field_name: str = Form(...),
        answer: str = Form(...),
    ):
        summary = _guest_case(request, token)
        candidate = summary.candidate
        if candidate is None:
            raise HTTPException(status_code=409, detail="No candidate exists")
        if field_name not in QUESTION_FIELD_NAMES:
            raise HTTPException(status_code=400, detail="Unsupported question")
        value = answer.strip()
        if not value:
            raise HTTPException(status_code=422, detail="An answer is required")
        try:
            _validate_candidate_input(field_name, value)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        candidate.fields[field_name] = CandidateField(value=value, source="guest_answer")
        _store(request).save_candidate(candidate)
        return RedirectResponse(request.url_for("guest_question", token=token), status_code=303)

    @app.get("/guest/{token}/confirm", response_class=HTMLResponse, name="guest_confirm")
    async def guest_confirm(request: Request, token: str):
        summary = _guest_case(request, token)
        if summary.candidate is None:
            return RedirectResponse(request.url_for("guest_capture", token=token), status_code=303)
        missing = summary.candidate.missing(REQUIRED_FIELD_NAMES)
        return templates.TemplateResponse(
            request,
            "guest_confirm.html",
            {
                "case": summary,
                "fields": _candidate_display(summary.candidate),
                "missing": missing,
            },
        )

    @app.post("/guest/{token}/confirm")
    async def guest_confirm_submit(request: Request, token: str):
        summary = _guest_case(request, token)
        candidate = summary.candidate
        if candidate is None:
            raise HTTPException(status_code=409, detail="No candidate exists")
        missing = candidate.missing(REQUIRED_FIELD_NAMES)
        if missing:
            raise HTTPException(status_code=422, detail=f"Missing mandatory fields: {', '.join(missing)}")
        candidate.guest_confirmed_at = utc_now()
        candidate.validated_at = utc_now()
        store = _store(request)
        store.save_candidate(candidate)
        store.save_filing_request(
            FilingRequest(
                case_id=candidate.case_id,
                candidate_sha256=store.candidate_sha256(candidate),
            )
        )
        store.update_status(
            candidate.case_id,
            CaseStatus.READY_FOR_FILING,
            "Guest confirmed one Filing Request; ready for the local worker",
        )
        return RedirectResponse(request.url_for("guest_done", token=token), status_code=303)

    @app.get("/guest/{token}/done", response_class=HTMLResponse, name="guest_done")
    async def guest_done(request: Request, token: str):
        summary = _guest_case(request, token, editable=False)
        return templates.TemplateResponse(request, "guest_done.html", {"case": summary})

    @app.get(
        "/mock-government/form-c/{case_id}",
        response_class=HTMLResponse,
        name="mock_form_c",
    )
    async def mock_form_c(request: Request, case_id: str):
        try:
            _store(request).get_summary(case_id)
        except CaseNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Case not found") from exc
        existing = _store(request).load_mock_submission(case_id)
        return templates.TemplateResponse(
            request,
            "mock_form_c.html",
            {"case_id": case_id, "fields": FORM_FIELDS, "submission": existing},
        )

    @app.post(
        "/mock-government/form-c/{case_id}",
        response_class=HTMLResponse,
        name="mock_form_c_submit",
    )
    async def mock_form_c_submit(request: Request, case_id: str):
        store = _store(request)
        try:
            store.get_summary(case_id)
        except CaseNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Case not found") from exc
        form = await request.form()
        values = {name: str(form.get(name, "")).strip() for name in REQUIRED_FIELD_NAMES}
        missing = [FIELD_BY_NAME[name].label for name, value in values.items() if not value]
        if missing:
            return templates.TemplateResponse(
                request,
                "mock_form_c.html",
                {
                    "case_id": case_id,
                    "fields": FORM_FIELDS,
                    "values": values,
                    "missing": missing,
                    "submission": None,
                },
                status_code=422,
            )
        existing = store.load_mock_submission(case_id)
        if existing is None:
            acknowledgement = f"MOCK-{case_id[-4:]}-{secrets.randbelow(9000) + 1000}"
            submission = MockSubmission(
                case_id=case_id,
                acknowledgement=acknowledgement,
                fields=values,
            )
            store.save_mock_submission(submission)
        else:
            if existing.fields != values:
                raise HTTPException(
                    status_code=409,
                    detail="Mock portal refuses a conflicting duplicate submission",
                )
            submission = existing
        return templates.TemplateResponse(
            request,
            "mock_receipt.html",
            {"submission": submission},
        )

    return app


app = create_app()
