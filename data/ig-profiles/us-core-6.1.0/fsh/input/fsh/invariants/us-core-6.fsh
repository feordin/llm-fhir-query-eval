Invariant: us-core-6
Description: "At least name.given and/or name.family are present or, if neither is available, the Data Absent Reason Extension is present."
* severity = #error
* expression = "(family.exists() or given.exists()) xor extension.where(url='http://hl7.org/fhir/StructureDefinition/data-absent-reason').exists()"
* xpath = "(/f:extension/@url='http://hl7.org/fhir/StructureDefinition/data-absent-reason' and not(/f:family or /f:given)) or (not(/f:extension/@url='http://hl7.org/fhir/StructureDefinition/data-absent-reason') and (/f:family or /f:given))"