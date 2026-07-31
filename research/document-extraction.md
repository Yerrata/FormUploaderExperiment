# Passport and Indian visa extraction strategy

## Decision

Retain two candidates for the final architecture:

1. **Lean hybrid:** Azure Document Intelligence `prebuilt-idDocument` for passport bio pages, an Azure custom extraction model for the resort's observed Indian visa/e-Visa layouts, and a local ICAO MRZ parser/validator. Add a paid multimodal API only as a second reader for unsupported visa layouts, never as the sole authority.
2. **Specialist hybrid:** Regula Document Reader SDK for passports and visas, plus the same independent local validation and correction rules. Carry this forward only if a representative benchmark and a commercial quote justify it.

Do not carry forward local OCR alone, AWS Textract AnalyzeID, Google's dedicated passport parser, or a multimodal model alone as end-to-end extraction architectures. Local MRZ code remains mandatory as a validator; multimodal vision remains useful as a gated second reader.

## Required output and trust model

The canonical record should preserve, for every proposed field: raw text, normalized value, source document/page and bounding region, extractor/model version, provider confidence when available, MRZ check result, cross-document comparison result, and final acceptance reason.

Passport MRZ (TD3) gives document type, issuing state, name, passport number, nationality, date of birth, sex, expiry and optional data. The visual zone additionally carries fields such as place of birth, issue date and authority. ICAO specifies check digits for passport number, birth date, expiry, optional data, and a composite check digit; it also warns that names can be transliterated or truncated. ([ICAO Doc 9303 Part 4](https://www.icao.int/sites/default/files/publications/DocSeries/9303_p4_cons_en.pdf))

Machine-readable visas (MRV-A/B) encode name, issuing state, document/passport or visa number, nationality, birth date, sex, valid-until date and optional data with check digits. Their visual zone can add valid-from, entries, visa type, duration/conditions and issue information. “Valid until” is not always equivalent to permitted duration of stay, so the system must not infer one from the other. ([ICAO Doc 9303 Part 7](https://www.icao.int/sites/default/files/publications/DocSeries/9303_p7_cons_en.pdf))

Acceptance must be rule-based:

- Passport number, birth date and expiry require valid MRZ check digits and agreement with the visual-zone extraction. Nationality and sex must pass closed-vocabulary checks. Name matching must allow ICAO transliteration/truncation rather than demand naive string equality.
- A visa with MRZ must pass its check digits and agree with the passport on identity and passport number where present. Visa number, type, valid-from/until, entries and stay duration remain distinct fields.
- A visa without usable MRZ requires either a benchmark-qualified specialist/template model or exact agreement between two independently configured readers, plus date/range and passport-link checks. Provider confidence alone is never acceptance evidence.
- Missing, contradictory or low-confidence critical fields trigger an automatic WhatsApp/web request for a clearer image or explicit guest correction. The workflow blocks if certainty is not restored; it never guesses.

## Options assessed

### Local OCR and MRZ parsing

Local processing is effectively free, keeps identity images on resort-controlled infrastructure, and can be fast with a purpose-built crop and OCR model. ICAO check digits provide unusually valuable deterministic error detection. Open-source parsers can support TD1/TD2/TD3 and MRV-A/B checks; for example, the `mrz` project implements ICAO formats and error reports. ([mrz checker](https://github.com/Arg0s1080/mrz))

It is not reliable enough as the sole extractor. PassportEye reports roughly 80% recognition on clearly visible MRZs in its developer's tests, imperfect precision, and around ten seconds for some documents; it also depends on Tesseract and has known layout/scan failure modes. ([PassportEye](https://github.com/konstantint/PassportEye)) Tesseract confidence is an OCR distance measure, not a calibrated probability that a Form C field is correct. ([Tesseract documentation](https://tesseract-ocr.github.io/tessdoc/tess3/FAQ-Old.html))

**Verdict:** mandatory validation and privacy-preserving fallback component, but excluded as a complete architecture.

### Specialised identity-document intelligence

Regula is the strongest documented candidate. Its SDK supports passports, visas, visual-zone OCR, MRZ, document identification, image-quality assessment and field validation across mobile, web and desktop. ([feature overview](https://docs.regulaforensics.com/develop/doc-reader-sdk/overview/features/)) Its April 2026 database reports 16,388 document templates across 254 countries/territories, and its product has an explicit Indian visa MRZ parser. ([9.3 release](https://docs.regulaforensics.com/develop/doc-reader-sdk/release-notes/9-3/), [Indian visa support](https://docs.regulaforensics.com/develop/doc-reader-sdk/release-notes/doc-reader-release-notes-4-12/)) It can run client-side/on-premises; Regula documents browser-only processing where images are not sent to a service. ([web processing](https://docs.regulaforensics.com/develop/doc-reader-sdk/release-notes/doc-reader-release-notes-6-8/))

The trade-off is procurement: pricing is quote-based, with a 30-day trial rather than a durable free tier. ([Regula product page](https://regulaforensics.com/products/document-reader-sdk/)) Microblink BlinkID also documents passport and India-visa support, visa type and entries, and a 30-day trial, but public evidence found here does not establish current Indian-visa production status or transparent recurring price strongly enough to prefer it. ([BlinkID changelog](https://docs.microblink.com/extraction/api/changelog), [trial](https://developer.microblink.com/license))

**Verdict:** include the Regula hybrid as the quality/coverage candidate, subject to an actual-document benchmark and acceptable quote.

### General document AI

Azure's prebuilt ID model explicitly supports worldwide passport books/cards and returns normalized fields plus the two 44-character MRZ lines. It does not cover visas. ([ID model](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/prebuilt/id-document?view=doc-intel-4.0.0)) Azure custom extraction can start with five labelled examples of one layout and returns field confidence, making it a practical route for the finite set of Indian visa/e-Visa layouts actually encountered. Five is a starting minimum, not evidence of production accuracy. ([custom extraction](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/train/custom-model?view=doc-intel-4.0.0), [confidence guidance](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/concept/accuracy-confidence?view=doc-intel-4.0.0))

Azure offers 500 pages/month free; paid pricing is per page and region. It is asynchronous, so latency varies with page/content size. Input/results are encrypted and temporarily stored in the resource region; analysis results are retained for 24 hours unless deleted sooner. ([pricing](https://azure.microsoft.com/en-us/pricing/details/document-intelligence/), [latency](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/model-overview?view=doc-intel-4.0.0), [privacy](https://learn.microsoft.com/en-us/azure/foundry/responsible-ai/document-intelligence/data-privacy-security), [early deletion](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/authentication/encrypt-data-at-rest?view=doc-intel-4.0.0))

AWS AnalyzeID is officially limited to US passports and US driver licences. Google's dedicated parser is likewise a US passport parser priced at $0.10/document; its general custom extractor is possible but needs labelled evaluation and offers no advantage over Azure for this small deployment. ([AWS limits](https://docs.aws.amazon.com/textract/latest/dg/limits-document.html), [Google processors](https://docs.cloud.google.com/document-ai/docs/pretrained-overview), [Google pricing](https://cloud.google.com/products/document-ai/pricing))

**Verdict:** include the Azure hybrid as the likely version-1 default.

### Multimodal model APIs

Vision APIs can read unfamiliar visa layouts and return schema-constrained JSON, but schema conformance does not make field values correct and they expose no calibrated per-field OCR confidence. OpenAI supports image input and Structured Outputs; API billing is separate from ChatGPT subscriptions. API data is not used for training by default, but abuse-monitoring logs may retain customer content for up to 30 days unless approved controls apply. ([vision](https://developers.openai.com/api/docs/guides/images-vision), [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs), [separate billing](https://help.openai.com/en/articles/8156019-how-can-i-move-my-chatgpt-subscription-to-the-api), [data controls](https://developers.openai.com/api/docs/guides/your-data))

Gemini offers free image-capable quotas, but Google's pricing page states free-tier content is used to improve products while paid-tier content is not. Passport images must therefore never use the unpaid tier. ([Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing), [paid-service restriction](https://ai.google.dev/gemini-api/docs/zdr))

**Verdict:** include only a paid, `store=false`/equivalent second-reader role after privacy review; exclude as sole extractor.

## Evaluation gate

Build a consented, access-controlled ground-truth set before selection:

- Stratify by passport country/material/layout; sticker visa versus e-Visa; visa category; language/script; phone; and pristine, glare, blur, crop, skew and low-light capture conditions.
- Use a locked test set unseen during custom-model training. Start model selection with at least 300 passport/visa pairs and deliberately difficult/invalid images; expand with production-equivalent samples before unattended release.
- Report per-field exact match after declared normalization, character error rate, MRZ/checksum detection, unsupported-document rejection, false-accept rate on each critical field, document-level all-critical-fields-correct rate, correction-request rate, straight-through rate, p50/p95 latency and cost.
- Calibrate thresholds only on training/validation data. Release only if the locked set has **zero accepted wrong critical fields** and the agreed document-level straight-through target is met. Every model/version change reruns the set; production drift is sampled and new layouts default to blocked.

The benchmark, not vendor confidence or marketing accuracy, decides between the Azure and Regula hybrids.
