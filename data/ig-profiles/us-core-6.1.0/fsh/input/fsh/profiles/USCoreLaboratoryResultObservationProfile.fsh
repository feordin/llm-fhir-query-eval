Profile: USCoreLaboratoryResultObservationProfile
Parent: http://hl7.org/fhir/us/core/StructureDefinition/us-core-observation-clinical-result
Id: us-core-observation-lab
Title: "US Core Laboratory Result Observation Profile"
Description: "The US Core Laboratory Result Observation Profile is based upon the US Core Observation Clinical Result Profile and, along with the US Core DiagnosticReport Profile for Laboratory Results Reporting, meets the U.S. Core Data for Interoperability (USCDI) Laboratory requirements. Laboratory results are grouped and summarized using the DiagnosticReport resource, which references Observation resources. Each Observation resource represents an individual laboratory test and result value, a “nested” panel (such as a microbial susceptibility panel) that references other observations, or rarely a laboratory test with component result values. The US Core Laboratory Result Observation Profile sets minimum expectations for the Observation resource to record, search, and fetch laboratory test results associated with a patient to promote interoperability and adoption through common implementation. It identifies which core elements, extensions, vocabularies, and value sets SHALL be present in the resource and constrains the way the elements are used when using this profile. It provides the floor for standards development for specific use cases."
* ^experimental = false
* ^date = "2022-11-19"
* category contains us-core 1..1 MS
* category[us-core] = http://terminology.hl7.org/CodeSystem/observation-category#laboratory
* category[us-core] ^extension.url = "http://hl7.org/fhir/us/core/StructureDefinition/uscdi-requirement"
* category[us-core] ^extension.valueBoolean = true
* category[us-core] ^short = "(USCDI) Classification of  type of observation"
* code MS
* code from http://hl7.org/fhir/us/core/ValueSet/us-core-laboratory-test-codes (extensible)
* code ^extension.url = "http://hl7.org/fhir/us/core/StructureDefinition/uscdi-requirement"
* code ^extension.valueBoolean = true
* code ^short = "(USCDI) Laboratory Test Name"
* code ^binding.description = "Laboratory LOINC Codes"
* value[x] only Quantity or CodeableConcept or string or boolean or integer or Range or Ratio or SampledData or time or dateTime or Period
* value[x] MS
* value[x] obeys us-core-4
* value[x] ^extension.url = "http://hl7.org/fhir/us/core/StructureDefinition/uscdi-requirement"
* value[x] ^extension.valueBoolean = true
* value[x] ^short = "(USCDI) Result Value"
* value[x] ^definition = "The Laboratory result value.  If a coded value,  the valueCodeableConcept.code **SHOULD** be selected from [SNOMED CT](http://hl7.org/fhir/ValueSet/uslab-obs-codedresults) if the concept exists. If a numeric value, valueQuantity.code **SHALL** be selected from [UCUM](http://unitsofmeasure.org).  A FHIR [UCUM Codes value set](http://hl7.org/fhir/STU3/valueset-ucum-units.html) that defines all UCUM codes is in the FHIR specification."
* value[x] ^type[0].extension.url = "http://hl7.org/fhir/StructureDefinition/elementdefinition-type-must-support"
* value[x] ^type[=].extension.valueBoolean = true
* value[x] ^type[+].extension.url = "http://hl7.org/fhir/StructureDefinition/elementdefinition-type-must-support"
* value[x] ^type[=].extension.valueBoolean = true
* value[x] ^type[+].extension.url = "http://hl7.org/fhir/StructureDefinition/elementdefinition-type-must-support"
* value[x] ^type[=].extension.valueBoolean = true
* value[x] ^condition = "us-core-4"
* specimen only Reference(http://hl7.org/fhir/us/core/StructureDefinition/us-core-specimen)
* specimen MS
* specimen ^extension.url = "http://hl7.org/fhir/us/core/StructureDefinition/uscdi-requirement"
* specimen ^extension.valueBoolean = true
* specimen ^short = "(USCDI) Specimen used for this observation"