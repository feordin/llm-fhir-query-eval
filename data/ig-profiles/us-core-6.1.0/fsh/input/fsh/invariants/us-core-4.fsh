Invariant: us-core-4
Description: "SHOULD use Snomed CT for coded Results"
* severity = #warning
* expression = "value.ofType(CodeableConcept).coding.system.empty() or value.ofType(CodeableConcept).coding.system = 'http://snomed.info/sct'"
* xpath = "not(exists(f:valueCodeableConcept/f:coding/f:system) ) or f:valueCodeableConcept/f:coding/f:system[@value='http://snomed.info/sct']"
* extension[0].url = "http://hl7.org/fhir/StructureDefinition/elementdefinition-bestpractice"
* extension[0].valueBoolean = true