// WARNING: The following Mapping may be incomplete since the original USCoreConditionEncounterDiagnosisProfile
// StructureDefinition was missing the mapping entry for argonaut-dq-dstu2.
// Please review this and add the following properties as necessary: Target, Title, Description
Mapping: argonaut-dq-dstu2-for-USCoreConditionEncounterDiagnosisProfile
Id: argonaut-dq-dstu2
Source: USCoreConditionEncounterDiagnosisProfile
* -> "Condition"
* clinicalStatus -> "Condition.clinicalStatus"
* verificationStatus -> "Condition.verificationStatus"
* category -> "Condition.category"
* code -> "Condition.code"
* subject -> "Condition.patient"