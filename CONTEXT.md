# Form C Filing

This context covers the collection, submission, and evidencing of Indian Form C information for foreign guests staying at the property.

## Language

**Form C Filing**:
One completed submission of a foreign guest's required stay and identity information to the government service.
_Avoid_: Application, policy filing

**Guest Input**:
Information or identity documents supplied directly by the guest, including answers requested after check-in.
_Avoid_: Staff intervention

**Fully Unattended Submission**:
A Form C Filing that proceeds from complete required input through validation, government submission, receipt retrieval, and evidence storage without staff action. Guest Input may occur before submission; bypassing or circumventing access controls is excluded.
_Avoid_: Fully automated when staff must complete a CAPTCHA or submission step

**Filing Evidence**:
The stored government acknowledgement or receipt, linked to the submitted Form C data and the relevant guest identity documents.
_Avoid_: Success message, screenshot-only proof

**Verified Filing**:
A Form C Filing whose government acceptance and submitted values are supported by Filing Evidence.
_Avoid_: A request sent to the portal, a successful click, or an HTTP success response

**Critical Field**:
A required guest identity, travel, or stay value whose incorrect value could misidentify the guest or make the filing materially incorrect.
_Avoid_: A field accepted only because an extraction confidence threshold was exceeded

**Supported Case**:
A case with valid supported documents, complete or obtainable Guest Input, and an available government service. Excluded cases remain separately counted and classified rather than disappearing from performance reporting.
_Avoid_: Any case removed after the system encounters difficulty

**Evidence Package**:
The tamper-evident history that connects source information, submitted values, submission attempts, and Filing Evidence for one guest stay.
_Avoid_: A receipt stored without the values and events it is meant to prove
